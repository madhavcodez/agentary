from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ..models.user import User
from ..models.voice_extraction import VoiceExtraction, CallRecord
from ..schemas.voice_extraction import (
    VoiceExtractionCreate, VoiceExtractionUpdate, VoiceExtractionResponse, CallRecordResponse,
)

router = APIRouter(prefix="/api/voice-extractions", tags=["voice"])


@router.post("", response_model=VoiceExtractionResponse, status_code=201)
def create_voice_extraction(
    body: VoiceExtractionCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    ve = VoiceExtraction(**body.model_dump())
    db.add(ve)
    db.commit()
    db.refresh(ve)
    return ve


@router.get("", response_model=list[VoiceExtractionResponse])
def list_voice_extractions(
    project_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(VoiceExtraction)
    if project_id:
        query = query.filter(VoiceExtraction.project_id == project_id)
    return query.order_by(VoiceExtraction.created_at.desc()).all()


@router.get("/{ve_id}", response_model=VoiceExtractionResponse)
def get_voice_extraction(
    ve_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    ve = db.query(VoiceExtraction).filter(VoiceExtraction.id == ve_id).first()
    if not ve:
        raise HTTPException(status_code=404, detail="Voice extraction not found")
    return ve


@router.get("/{ve_id}/calls", response_model=list[CallRecordResponse])
def list_call_records(
    ve_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return db.query(CallRecord).filter(CallRecord.voice_extraction_id == ve_id).order_by(CallRecord.created_at.desc()).all()
