from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..deps import get_current_user, get_db
from ..models.match import Match
from ..models.pipeline import PipelineStage
from ..models.user import User
from ..schemas.match import MatchAction, MatchList, MatchResponse
from ..schemas.pipeline import PipelineSummary, StageUpdate
from ..services.pipeline_engine import advance_stage

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=MatchList)
def list_matches(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    min_score: float | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        db.query(Match)
        .options(joinedload(Match.opportunity))
        .filter(Match.user_id == user.id)
    )

    if status:
        query = query.filter(Match.status == status)
    if min_score is not None:
        query = query.filter(Match.composite_score >= min_score)

    total = query.count()
    items = (
        query.order_by(Match.composite_score.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return MatchList(items=items, total=total, page=page, limit=limit)


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(
    match_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    match = (
        db.query(Match)
        .options(joinedload(Match.opportunity))
        .filter(Match.id == match_id, Match.user_id == user.id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.post("/{match_id}/action", response_model=MatchResponse)
def update_match_status(
    match_id: UUID,
    body: MatchAction,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    match = (
        db.query(Match)
        .filter(Match.id == match_id, Match.user_id == user.id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    match.status = body.status
    db.commit()
    db.refresh(match)
    return match


@router.get("/pipeline-summary", response_model=PipelineSummary)
def pipeline_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(Match.pipeline_stage, func.count(Match.id))
        .filter(Match.user_id == user.id)
        .group_by(Match.pipeline_stage)
        .all()
    )
    counts = {stage: count for stage, count in rows}
    return PipelineSummary(
        lead=counts.get("lead", 0),
        contacted=counts.get("contacted", 0),
        aware=counts.get("aware", 0),
        engaged=counts.get("engaged", 0),
        meeting=counts.get("meeting", 0),
        closed_won=counts.get("closed_won", 0),
        closed_lost=counts.get("closed_lost", 0),
        paused=counts.get("paused", 0),
    )


@router.put("/{match_id}/stage", response_model=MatchResponse)
def update_stage(
    match_id: UUID,
    body: StageUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Validate that the match belongs to this user
    match = (
        db.query(Match)
        .options(joinedload(Match.opportunity))
        .filter(Match.id == match_id, Match.user_id == user.id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    try:
        new_stage = PipelineStage(body.stage)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stage: {body.stage}. Valid stages: {[s.value for s in PipelineStage]}",
        )

    advanced = advance_stage(db, match_id, new_stage, body.trigger)
    if not advanced:
        raise HTTPException(
            status_code=409,
            detail="Stage transition not allowed (can only advance forward unless trigger is 'manual')",
        )

    db.refresh(match)
    return match


@router.post("/score")
async def score_matches(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.match_engine import score_all_matches
    result = await score_all_matches(db, user_id=user.id)
    return result
