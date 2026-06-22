"""Celery tasks for insight and recommendation generation."""

from __future__ import annotations

import asyncio
import logging

from .celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.insight_tasks.generate_insights_for_entity",
    bind=True,
    max_retries=1,
    soft_time_limit=600,
)
def generate_insights_for_entity(self, entity_id: str, project_id: str) -> dict:
    """Generate insights and recommendations for a single entity."""
    from ..database import SessionLocal
    from ..services.intelligence.insight_generator import InsightGenerator
    from ..services.intelligence.recommendation_generator import RecommendationGenerator

    db = SessionLocal()
    try:
        ig = InsightGenerator(db)
        insights = asyncio.run(ig.generate_for_entity(entity_id, project_id))

        rec_count = 0
        if insights:
            rg = RecommendationGenerator(db)
            recs = asyncio.run(rg.generate_from_insights(project_id, entity_id))
            rec_count = len(recs)

        db.commit()
        return {"insights": len(insights), "recommendations": rec_count}
    except Exception as exc:
        db.rollback()
        logger.exception("Insight generation failed for entity %s", entity_id)
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.insight_tasks.generate_project_insights",
    bind=True,
    max_retries=1,
    soft_time_limit=600,
)
def generate_project_insights(self, project_id: str) -> dict:
    """Generate project-level insights and recommendations."""
    from ..database import SessionLocal
    from ..services.intelligence.insight_generator import InsightGenerator
    from ..services.intelligence.recommendation_generator import RecommendationGenerator

    db = SessionLocal()
    try:
        ig = InsightGenerator(db)
        insights = asyncio.run(ig.generate_for_project(project_id))

        rec_count = 0
        if insights:
            rg = RecommendationGenerator(db)
            recs = asyncio.run(rg.generate_from_insights(project_id))
            rec_count = len(recs)

        db.commit()
        return {"insights": len(insights), "recommendations": rec_count}
    except Exception as exc:
        db.rollback()
        logger.exception("Project insight generation failed for %s", project_id)
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.insight_tasks.mark_stale_insights",
    soft_time_limit=300,
)
def mark_stale_insights() -> dict:
    """Mark insights as stale based on their freshness threshold."""
    from ..database import SessionLocal
    from ..services.intelligence.insight_service import InsightService

    db = SessionLocal()
    try:
        svc = InsightService(db)
        count = svc.mark_stale()
        db.commit()
        return {"stale_count": count}
    finally:
        db.close()
