"""API routes for insights — list, detail, evidence chain, generation."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User
from ..schemas.intelligence import EvidenceResponse, InsightResponse
from ..services.intelligence.evidence_service import EvidenceService
from ..services.intelligence.insight_service import InsightService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("", response_model=list[InsightResponse])
def list_insights(
    project_id: UUID = Query(...),
    entity_id: UUID | None = None,
    insight_type: str | None = None,
    include_stale: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List insights with optional filters."""
    svc = InsightService(db)
    if entity_id:
        return svc.list_for_entity(
            entity_id=entity_id,
            include_stale=include_stale,
            limit=limit,
            offset=offset,
        )
    return svc.list_for_project(
        project_id=project_id,
        insight_type=insight_type,
        include_stale=include_stale,
        limit=limit,
        offset=offset,
    )


@router.get("/{insight_id}", response_model=InsightResponse)
def get_insight(
    insight_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get insight detail with evidence chain."""
    svc = InsightService(db)
    insight = svc.get_insight(insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    return insight


@router.get("/{insight_id}/evidence", response_model=list[EvidenceResponse])
def get_insight_evidence(
    insight_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get the evidence chain for an insight."""
    svc = InsightService(db)
    insight = svc.get_insight(insight_id)
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    ev_svc = EvidenceService(db)
    return ev_svc.get_evidence_chain(insight_id=insight_id)


@router.post("/generate")
async def trigger_insight_generation(
    project_id: UUID = Query(...),
    entity_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Manually trigger insight (and recommendation) generation.

    Attempts to dispatch to Celery. If Celery is unavailable, runs
    inline as a fallback so the feature still works without a broker.
    """
    if entity_id:
        try:
            from ..tasks.insight_tasks import generate_insights_for_entity

            generate_insights_for_entity.delay(str(entity_id), str(project_id))
            return {"status": "queued", "scope": "entity", "entity_id": str(entity_id)}
        except Exception:
            logger.warning("Celery unavailable, running insight generation inline")
            from ..services.intelligence.insight_generator import InsightGenerator
            from ..services.intelligence.recommendation_generator import RecommendationGenerator

            ig = InsightGenerator(db)
            insights = await ig.generate_for_entity(entity_id, project_id)
            recs = []
            if insights:
                rg = RecommendationGenerator(db)
                recs = await rg.generate_from_insights(project_id, entity_id)
            db.commit()
            return {
                "status": "completed",
                "scope": "entity",
                "insights_generated": len(insights),
                "recommendations_generated": len(recs),
            }
    else:
        try:
            from ..tasks.insight_tasks import generate_project_insights

            generate_project_insights.delay(str(project_id))
            return {"status": "queued", "scope": "project"}
        except Exception:
            logger.warning("Celery unavailable, running project insight generation inline")
            from ..services.intelligence.insight_generator import InsightGenerator
            from ..services.intelligence.recommendation_generator import RecommendationGenerator

            ig = InsightGenerator(db)
            insights = await ig.generate_for_project(project_id)
            recs = []
            if insights:
                rg = RecommendationGenerator(db)
                recs = await rg.generate_from_insights(project_id)
            db.commit()
            return {
                "status": "completed",
                "scope": "project",
                "insights_generated": len(insights),
                "recommendations_generated": len(recs),
            }
