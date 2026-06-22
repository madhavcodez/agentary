"""API routes for voice extraction sessions and call records."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User
from ..models.voice_extraction import CallRecord, CallStatus, VoiceExtraction
from ..schemas.voice import (
    CallRecordList,
    CallRecordResponse,
    ExtractionResultResponse,
    VoiceExtractionCreate,
    VoiceExtractionList,
    VoiceExtractionResponse,
)
from ..services.voice import templates, voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice/sessions", tags=["voice-sessions"])


@router.post("", response_model=VoiceExtractionResponse, status_code=201)
async def create_session(
    body: VoiceExtractionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new voice extraction session."""
    data = body.model_dump()

    # If a template name is provided, merge template defaults
    if body.template_name:
        template = templates.get_template_by_name(body.template_name)
        if not template:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown template: {body.template_name}",
            )
        # Template provides defaults; explicit values override
        if not data.get("persona"):
            data["persona"] = template["persona"]
        if not data.get("extraction_schema") or not data["extraction_schema"].get("fields"):
            data["extraction_schema"] = template["extraction_schema"]
        if not data.get("objective"):
            data["objective"] = template["objective"]

    ve = await voice_service.create_voice_extraction(data, db)

    # If targets were provided, plan calls immediately
    if body.targets:
        await voice_service.plan_calls(ve, body.targets, db)

    db.commit()
    db.refresh(ve)
    return ve


@router.get("", response_model=VoiceExtractionList)
def list_sessions(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    project_id: UUID | None = None,
    mission_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List voice extraction sessions with optional filters."""
    query = db.query(VoiceExtraction).join(
        # Filter by projects the user has access to
        # For now, just filter by project ownership
    )

    if project_id:
        query = query.filter(VoiceExtraction.project_id == project_id)
    if mission_id:
        query = query.filter(VoiceExtraction.mission_id == mission_id)
    if status:
        query = query.filter(VoiceExtraction.status == status)

    total = query.count()
    items = (
        query.order_by(VoiceExtraction.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return VoiceExtractionList(items=items, total=total, page=page, limit=limit)


@router.get("/{session_id}", response_model=VoiceExtractionResponse)
def get_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a voice extraction session by ID."""
    ve = db.query(VoiceExtraction).filter(VoiceExtraction.id == session_id).first()
    if not ve:
        raise HTTPException(status_code=404, detail="Voice extraction not found")
    return ve


@router.get("/{session_id}/calls", response_model=CallRecordList)
def list_calls(
    session_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all call records for a voice extraction session."""
    records = (
        db.query(CallRecord)
        .filter(CallRecord.voice_extraction_id == session_id)
        .order_by(CallRecord.created_at.desc())
        .all()
    )
    return CallRecordList(items=records, total=len(records))


@router.get("/{session_id}/calls/{call_id}", response_model=CallRecordResponse)
def get_call(
    session_id: UUID,
    call_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a specific call record with transcript and extraction."""
    record = (
        db.query(CallRecord)
        .filter(
            CallRecord.id == call_id,
            CallRecord.voice_extraction_id == session_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Call record not found")
    return record


@router.post("/{session_id}/calls/{call_id}/start")
async def start_call(
    session_id: UUID,
    call_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Initiate a call for a specific call record."""
    record = (
        db.query(CallRecord)
        .filter(
            CallRecord.id == call_id,
            CallRecord.voice_extraction_id == session_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Call record not found")

    if record.status not in (CallStatus.pending,):
        raise HTTPException(
            status_code=409,
            detail=f"Call is already {record.status.value}",
        )

    result = await voice_service.start_call(call_id, db)
    return result


@router.post("/{session_id}/calls/{call_id}/stop")
async def stop_call(
    session_id: UUID,
    call_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stop an in-progress call."""
    from ..services.twilio_client import end_call

    record = (
        db.query(CallRecord)
        .filter(
            CallRecord.id == call_id,
            CallRecord.voice_extraction_id == session_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Call record not found")

    if record.provider_call_id and not record.provider_call_id.startswith("SIM_"):
        await end_call(record.provider_call_id)

    record.status = CallStatus.completed
    db.add(record)
    db.commit()
    return {"status": "stopped"}


@router.get("/{session_id}/calls/{call_id}/transcript")
def get_transcript(
    session_id: UUID,
    call_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get transcript for a specific call."""
    record = (
        db.query(CallRecord)
        .filter(
            CallRecord.id == call_id,
            CallRecord.voice_extraction_id == session_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Call record not found")
    return {"transcript": record.transcript}


@router.get(
    "/{session_id}/calls/{call_id}/extraction",
    response_model=ExtractionResultResponse,
)
def get_extraction(
    session_id: UUID,
    call_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get extraction results for a specific call."""
    record = (
        db.query(CallRecord)
        .filter(
            CallRecord.id == call_id,
            CallRecord.voice_extraction_id == session_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Call record not found")

    return ExtractionResultResponse(
        fields=[
            {"field_name": k, "value": v, "confidence": record.extraction_confidence or 0}
            for k, v in (record.extracted_data or {}).items()
        ],
        overall_confidence=record.extraction_confidence or 0,
        quality_score=0,  # Would need to recompute from goals
    )


@router.post("/{session_id}/calls/{call_id}/reextract")
async def reextract(
    session_id: UUID,
    call_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Re-run extraction on an existing transcript."""
    record = (
        db.query(CallRecord)
        .filter(
            CallRecord.id == call_id,
            CallRecord.voice_extraction_id == session_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Call record not found")

    if not record.transcript:
        raise HTTPException(status_code=400, detail="No transcript available")

    result = await voice_service.process_completed_call(call_id, db)
    return result
