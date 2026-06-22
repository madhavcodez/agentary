"""API routes for signals — list, detail, manual creation."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.signal import SignalSourceType, SignalType
from ..models.user import User
from ..schemas.intelligence import ObservationResponse, SignalCreate, SignalResponse
from ..services.intelligence.observation_service import ObservationService
from ..services.intelligence.signal_service import SignalService

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("", response_model=list[SignalResponse])
def list_signals(
    project_id: UUID = Query(...),
    source_type: str | None = None,
    signal_type: str | None = None,
    entity_id: UUID | None = None,
    is_processed: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List signals with optional filters."""
    svc = SignalService(db)
    return svc.list_signals(
        project_id=project_id,
        source_type=source_type,
        signal_type=signal_type,
        entity_id=entity_id,
        is_processed=is_processed,
        limit=limit,
        offset=offset,
    )


@router.get("/{signal_id}", response_model=SignalResponse)
def get_signal(
    signal_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get signal detail."""
    svc = SignalService(db)
    signal = svc.get_signal(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.get("/{signal_id}/observations", response_model=list[ObservationResponse])
def get_signal_observations(
    signal_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get observations linked to a signal."""
    svc = SignalService(db)
    signal = svc.get_signal(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    obs_svc = ObservationService(db)
    return obs_svc.list_for_signal(signal_id)


@router.post("", response_model=SignalResponse, status_code=201)
def create_signal(
    body: SignalCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually create a user-flagged signal."""
    svc = SignalService(db)
    signal = svc.create_signal(
        project_id=body.project_id,
        user_id=user.id,
        source_type=SignalSourceType(body.source_type),
        signal_type=SignalType(body.signal_type),
        title=body.title,
        content=body.content,
        structured_data=body.structured_data,
        source_id=body.source_id,
        entity_id=body.entity_id,
        confidence=body.confidence,
    )
    db.commit()
    return signal
