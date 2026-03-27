"""Evidence linking between observations and insights/recommendations."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.evidence import Evidence, EvidenceType

logger = logging.getLogger(__name__)


class EvidenceService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def link_evidence(
        self,
        observation_id: UUID,
        insight_id: UUID | None = None,
        recommendation_id: UUID | None = None,
        evidence_type: EvidenceType = EvidenceType.supporting,
        weight: float = 1.0,
        notes: str | None = None,
    ) -> Evidence:
        """Link an observation to an insight or recommendation as evidence."""
        if not insight_id and not recommendation_id:
            raise ValueError("Either insight_id or recommendation_id must be provided")

        evidence = Evidence(
            observation_id=observation_id,
            insight_id=insight_id,
            recommendation_id=recommendation_id,
            evidence_type=evidence_type,
            weight=weight,
            notes=notes,
        )
        self.db.add(evidence)
        self.db.flush()
        return evidence

    def get_evidence_chain(
        self,
        insight_id: UUID | None = None,
        recommendation_id: UUID | None = None,
    ) -> list[Evidence]:
        """Get the full evidence chain for an insight or recommendation."""
        q = self.db.query(Evidence)
        if insight_id:
            q = q.filter(Evidence.insight_id == insight_id)
        elif recommendation_id:
            q = q.filter(Evidence.recommendation_id == recommendation_id)
        else:
            return []
        return q.order_by(Evidence.created_at.desc()).all()
