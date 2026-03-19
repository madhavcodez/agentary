from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..deps import get_db
from ..models.match import Match
from ..schemas.match import MatchAction, MatchList, MatchResponse

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=MatchList)
def list_matches(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    min_score: float | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Match).options(joinedload(Match.opportunity))

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
def get_match(match_id: UUID, db: Session = Depends(get_db)):
    match = (
        db.query(Match)
        .options(joinedload(Match.opportunity))
        .filter(Match.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.post("/{match_id}/action", response_model=MatchResponse)
def update_match_status(match_id: UUID, body: MatchAction, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    match.status = body.status
    db.commit()
    db.refresh(match)
    return match


@router.post("/score")
async def score_matches(db: Session = Depends(get_db)):
    from ..services.match_engine import score_all_matches
    result = await score_all_matches(db)
    return result
