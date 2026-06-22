from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.match import Match
from ..models.research import ResearchResult
from ..models.user import User
from ..schemas.research import ResearchResponse, ResearchSummary

router = APIRouter(prefix="/research", tags=["research"])


@router.post("/{match_id}", response_model=ResearchSummary)
async def trigger_research(
    match_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger deep research for a match.

    Runs Gemini Search grounding and Exa contact discovery in parallel,
    stores results, and auto-creates Contact records.
    """
    match = db.query(Match).filter(Match.id == match_id, Match.user_id == user.id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    from ..services.research.engine import deep_research

    result = await deep_research(db, match, user_id=user.id)

    company_intel = result.get("company_intel", {})
    return ResearchSummary(
        match_id=match_id,
        company_intel_keys=list(company_intel.keys()) if isinstance(company_intel, dict) else [],
        contacts_found_count=result.get("contacts_found", 0),
        quality_score=result.get("quality_score", 0.0),
        sources_used=result.get("sources_used", []),
    )


@router.get("/{match_id}", response_model=ResearchResponse)
def get_research(
    match_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get research results for a match."""
    research = (
        db.query(ResearchResult)
        .filter(ResearchResult.match_id == match_id, ResearchResult.user_id == user.id)
        .first()
    )
    if not research:
        raise HTTPException(
            status_code=404,
            detail="No research found for this match. Trigger research first via POST.",
        )
    return research
