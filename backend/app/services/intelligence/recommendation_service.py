"""Recommendation creation, review workflow, and retrieval."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.recommendation import (
    Recommendation,
    RecommendationPriority,
    RecommendationStatus,
    RecommendationType,
)

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_recommendation(
        self,
        project_id: UUID,
        recommendation_type: RecommendationType,
        title: str,
        rationale: str | None = None,
        suggested_action: dict | None = None,
        entity_id: UUID | None = None,
        insight_id: UUID | None = None,
        confidence: float | None = None,
        priority: RecommendationPriority = RecommendationPriority.medium,
        expires_at: datetime | None = None,
    ) -> Recommendation:
        """Create a recommendation, optionally linked to an insight."""
        rec = Recommendation(
            project_id=project_id,
            recommendation_type=recommendation_type,
            title=title,
            rationale=rationale,
            suggested_action=suggested_action or {},
            entity_id=entity_id,
            insight_id=insight_id,
            confidence=confidence,
            priority=priority,
            expires_at=expires_at,
        )
        self.db.add(rec)
        self.db.flush()
        return rec

    def accept(self, recommendation_id: UUID, reviewed_by: UUID) -> Recommendation | None:
        """Accept a recommendation."""
        rec = self.db.query(Recommendation).filter_by(id=recommendation_id).first()
        if not rec:
            return None
        rec.status = RecommendationStatus.accepted
        rec.reviewed_by = reviewed_by
        rec.reviewed_at = datetime.now(timezone.utc)
        self.db.flush()
        return rec

    def reject(
        self,
        recommendation_id: UUID,
        reviewed_by: UUID,
        reason: str | None = None,
    ) -> Recommendation | None:
        """Reject a recommendation with an optional reason."""
        rec = self.db.query(Recommendation).filter_by(id=recommendation_id).first()
        if not rec:
            return None
        rec.status = RecommendationStatus.rejected
        rec.reviewed_by = reviewed_by
        rec.reviewed_at = datetime.now(timezone.utc)
        rec.rejection_reason = reason
        self.db.flush()
        return rec

    def list_pending(
        self,
        project_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Recommendation]:
        """Get pending recommendations sorted by priority (critical first)."""
        priority_order = [
            RecommendationPriority.critical,
            RecommendationPriority.high,
            RecommendationPriority.medium,
            RecommendationPriority.low,
        ]
        recs = (
            self.db.query(Recommendation)
            .filter(
                Recommendation.project_id == project_id,
                Recommendation.status == RecommendationStatus.pending,
            )
            .order_by(Recommendation.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        # Sort by priority order in Python since enum ordering in SQL varies
        priority_rank = {p: i for i, p in enumerate(priority_order)}
        return sorted(recs, key=lambda r: priority_rank.get(r.priority, 99))

    def list_for_project(
        self,
        project_id: UUID,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Recommendation]:
        """List all recommendations for a project."""
        q = self.db.query(Recommendation).filter(
            Recommendation.project_id == project_id
        )
        if status:
            q = q.filter(Recommendation.status == status)
        return q.order_by(Recommendation.created_at.desc()).offset(offset).limit(limit).all()

    def get_recommendation(self, recommendation_id: UUID) -> Recommendation | None:
        """Get a single recommendation by ID."""
        return self.db.query(Recommendation).filter_by(id=recommendation_id).first()
