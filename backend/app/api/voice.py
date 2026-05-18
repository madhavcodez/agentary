from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.project import Project
from ..models.user import User
from ..models.voice_extraction import CallRecord, VoiceExtraction
from ..schemas.voice_extraction import (
    CallRecordResponse,
    VoiceExtractionCreate,
    VoiceExtractionResponse,
)

router = APIRouter(prefix="/api/voice-extractions", tags=["voice"])


def _owned_voice_extraction(
    db: Session, ve_id: UUID, user: User
) -> VoiceExtraction:
    """Load a voice extraction only if the caller owns the parent project.

    Without this join, any authenticated user can read any voice extraction
    (including transcripts and extracted personal data) by guessing a UUID.
    """
    ve = (
        db.query(VoiceExtraction)
        .join(Project, Project.id == VoiceExtraction.project_id)
        .filter(VoiceExtraction.id == ve_id, Project.user_id == user.id)
        .first()
    )
    if not ve:
        raise HTTPException(status_code=404, detail="Voice extraction not found")
    return ve


@router.post("", response_model=VoiceExtractionResponse, status_code=201)
def create_voice_extraction(
    body: VoiceExtractionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a voice extraction. Verifies the caller owns the parent project."""
    project = (
        db.query(Project)
        .filter(Project.id == body.project_id, Project.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ve = VoiceExtraction(**body.model_dump())
    db.add(ve)
    db.commit()
    db.refresh(ve)
    return ve


@router.get("", response_model=list[VoiceExtractionResponse])
def list_voice_extractions(
    project_id: UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List voice extractions scoped to the caller's projects."""
    query = (
        db.query(VoiceExtraction)
        .join(Project, Project.id == VoiceExtraction.project_id)
        .filter(Project.user_id == user.id)
    )
    if project_id:
        query = query.filter(VoiceExtraction.project_id == project_id)
    return (
        query.order_by(VoiceExtraction.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{ve_id}", response_model=VoiceExtractionResponse)
def get_voice_extraction(
    ve_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _owned_voice_extraction(db, ve_id, user)


@router.get("/{ve_id}/calls", response_model=list[CallRecordResponse])
def list_call_records(
    ve_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List call records for a voice extraction. Ownership-checked."""
    # _owned_voice_extraction raises 404 if not owned, so we can safely query
    _owned_voice_extraction(db, ve_id, user)
    return (
        db.query(CallRecord)
        .filter(CallRecord.voice_extraction_id == ve_id)
        .order_by(CallRecord.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
