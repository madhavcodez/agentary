"""API routes for recommendations — list, inbox, accept/reject."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User
from ..schemas.intelligence import RecommendationResponse, RecommendationUpdate
from ..services.intelligence.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("", response_model=list[RecommendationResponse])
def list_recommendations(
    project_id: UUID = Query(...),
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List recommendations with optional status filter."""
    svc = RecommendationService(db)
    return svc.list_for_project(
        project_id=project_id,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/inbox", response_model=list[RecommendationResponse])
def recommendation_inbox(
    project_id: UUID = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get pending recommendations sorted by priority."""
    svc = RecommendationService(db)
    return svc.list_pending(
        project_id=project_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get recommendation detail."""
    svc = RecommendationService(db)
    rec = svc.get_recommendation(recommendation_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


@router.put("/{recommendation_id}/accept", response_model=RecommendationResponse)
def accept_recommendation(
    recommendation_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Accept a recommendation."""
    svc = RecommendationService(db)
    rec = svc.accept(recommendation_id, reviewed_by=user.id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    db.commit()
    return rec


@router.put("/{recommendation_id}/reject", response_model=RecommendationResponse)
def reject_recommendation(
    recommendation_id: UUID,
    body: RecommendationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reject a recommendation with optional reason."""
    svc = RecommendationService(db)
    rec = svc.reject(
        recommendation_id,
        reviewed_by=user.id,
        reason=body.rejection_reason,
    )
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    db.commit()
    return rec
