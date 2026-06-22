"""API routes for batch voice calling operations."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User
from ..models.voice_extraction import VoiceExtraction
from ..schemas.voice import (
    BatchCallRequest,
    BatchCallResponse,
    BatchResultsResponse,
    BatchStatusResponse,
)
from ..services.voice import voice_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice/batch", tags=["voice-batch"])


@router.post("", response_model=BatchCallResponse, status_code=201)
async def create_batch(
    body: BatchCallRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Plan a batch of calls for an existing voice extraction."""
    ve = db.query(VoiceExtraction).filter(VoiceExtraction.id == body.voice_extraction_id).first()
    if not ve:
        raise HTTPException(status_code=404, detail="Voice extraction not found")

    targets = [t.model_dump() for t in body.targets]
    records = await voice_service.plan_calls(ve, targets, db)
    db.commit()

    return BatchCallResponse(
        voice_extraction_id=ve.id,
        total=len(targets),
        planned=len(records),
        call_record_ids=[r.id for r in records],
    )


@router.get("/{batch_id}", response_model=BatchStatusResponse)
def get_batch_status(
    batch_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get status of a voice extraction batch."""
    status = voice_service.get_extraction_status(batch_id, db)
    return BatchStatusResponse(
        voice_extraction_id=batch_id,
        **{k: v for k, v in status.items() if k != "id" and k != "name"},
    )


@router.post("/{batch_id}/execute", response_model=BatchResultsResponse)
async def execute_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Execute all pending calls in a batch sequentially."""
    ve = db.query(VoiceExtraction).filter(VoiceExtraction.id == batch_id).first()
    if not ve:
        raise HTTPException(status_code=404, detail="Voice extraction not found")

    result = await voice_service.execute_batch(batch_id, db)
    return BatchResultsResponse(voice_extraction_id=batch_id, **result)


@router.get("/{batch_id}/results", response_model=BatchResultsResponse)
def get_batch_results(
    batch_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get aggregated results for a completed batch."""
    from ..models.voice_extraction import CallRecord, CallStatus

    ve = db.query(VoiceExtraction).filter(VoiceExtraction.id == batch_id).first()
    if not ve:
        raise HTTPException(status_code=404, detail="Voice extraction not found")

    records = db.query(CallRecord).filter(CallRecord.voice_extraction_id == batch_id).all()

    completed = 0
    failed = 0
    results = []
    for r in records:
        status_val = r.status.value if hasattr(r.status, "value") else str(r.status)
        if r.status == CallStatus.completed:
            completed += 1
        elif r.status == CallStatus.failed:
            failed += 1
        results.append(
            {
                "call_record_id": str(r.id),
                "target_name": r.target_name,
                "status": status_val,
                "extracted_data": r.extracted_data,
                "extraction_confidence": r.extraction_confidence,
            }
        )

    return BatchResultsResponse(
        voice_extraction_id=batch_id,
        total=len(records),
        completed=completed,
        failed=failed,
        results=results,
    )
