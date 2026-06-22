"""Insight creation, staleness management, and retrieval."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.evidence import EvidenceType
from ...models.insight import Insight, InsightType
from .evidence_service import EvidenceService

logger = logging.getLogger(__name__)


class InsightService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._evidence = EvidenceService(db)

    def create_insight(
        self,
        project_id: UUID,
        insight_type: InsightType,
        title: str,
        content: str | None = None,
        structured_data: dict | None = None,
        entity_id: UUID | None = None,
        confidence: float | None = None,
        staleness_threshold_hours: int = 168,
        observation_ids: list[UUID] | None = None,
    ) -> Insight:
        """Create an insight, optionally linking observations as evidence."""
        insight = Insight(
            project_id=project_id,
            insight_type=insight_type,
            title=title,
            content=content,
            structured_data=structured_data or {},
            entity_id=entity_id,
            confidence=confidence,
            staleness_threshold_hours=staleness_threshold_hours,
        )
        self.db.add(insight)
        self.db.flush()

        for obs_id in observation_ids or []:
            self._evidence.link_evidence(
                observation_id=obs_id,
                insight_id=insight.id,
                evidence_type=EvidenceType.supporting,
            )

        return insight

    def list_for_entity(
        self,
        entity_id: UUID,
        include_stale: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Insight]:
        """Get insights for a specific entity."""
        q = self.db.query(Insight).filter(
            Insight.entity_id == entity_id, Insight.is_active.is_(True)
        )
        if not include_stale:
            q = q.filter(Insight.is_stale.is_(False))
        return q.order_by(Insight.created_at.desc()).offset(offset).limit(limit).all()

    def list_for_project(
        self,
        project_id: UUID,
        insight_type: str | None = None,
        include_stale: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Insight]:
        """List all insights for a project."""
        q = self.db.query(Insight).filter(
            Insight.project_id == project_id, Insight.is_active.is_(True)
        )
        if insight_type:
            q = q.filter(Insight.insight_type == insight_type)
        if not include_stale:
            q = q.filter(Insight.is_stale.is_(False))
        return q.order_by(Insight.created_at.desc()).offset(offset).limit(limit).all()

    def get_insight(self, insight_id: UUID) -> Insight | None:
        """Get a single insight by ID."""
        return self.db.query(Insight).filter(Insight.id == insight_id).first()

    def mark_stale(self) -> int:
        """Mark insights as stale based on their freshness threshold. Returns count updated."""
        now = datetime.now(UTC)
        insights = (
            self.db.query(Insight)
            .filter(Insight.is_stale.is_(False), Insight.is_active.is_(True))
            .all()
        )
        count = 0
        for insight in insights:
            threshold = timedelta(hours=insight.staleness_threshold_hours)
            if insight.freshness_at and (now - insight.freshness_at) > threshold:
                insight.is_stale = True
                count += 1
        if count > 0:
            self.db.flush()
            logger.info("Marked %d insights as stale", count)
        return count
