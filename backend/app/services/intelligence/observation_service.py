"""Observation creation and retrieval."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.finding import Finding
from ...models.observation import Observation, ObservationType

logger = logging.getLogger(__name__)


class ObservationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_observation(
        self,
        project_id: UUID,
        observation_type: ObservationType,
        subject: str,
        content: str | None = None,
        structured_value: dict | None = None,
        entity_id: UUID | None = None,
        signal_id: UUID | None = None,
        finding_id: UUID | None = None,
        run_id: UUID | None = None,
        source_type: str | None = None,
        source_url: str | None = None,
        source_name: str | None = None,
        observed_at: datetime | None = None,
        confidence: float | None = None,
    ) -> Observation:
        """Create an observation record."""
        observation = Observation(
            project_id=project_id,
            observation_type=observation_type,
            subject=subject,
            content=content,
            structured_value=structured_value or {},
            entity_id=entity_id,
            signal_id=signal_id,
            finding_id=finding_id,
            run_id=run_id,
            source_type=source_type,
            source_url=source_url,
            source_name=source_name,
            observed_at=observed_at or datetime.now(UTC),
            confidence=confidence,
        )
        self.db.add(observation)
        self.db.flush()
        return observation

    def list_for_entity(
        self,
        entity_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Observation]:
        """Get observations for an entity."""
        return (
            self.db.query(Observation)
            .filter(Observation.entity_id == entity_id)
            .order_by(Observation.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def list_for_signal(self, signal_id: UUID) -> list[Observation]:
        """Get observations linked to a signal."""
        return (
            self.db.query(Observation)
            .filter(Observation.signal_id == signal_id)
            .order_by(Observation.created_at.desc())
            .all()
        )

    def create_from_finding(
        self, finding: Finding, project_id: UUID | None = None
    ) -> Observation | None:
        """Convert a Finding into an Observation, linking them.

        Idempotent: if the finding already has an observation_id, returns None.
        """
        if hasattr(finding, "observation_id") and finding.observation_id:
            return None  # Already migrated

        type_map = {
            "fact": ObservationType.fact,
            "data_point": ObservationType.measurement,
            "quote": ObservationType.quote,
            "statistic": ObservationType.measurement,
            "insight": ObservationType.classification,
            "sentiment": ObservationType.classification,
            "trend": ObservationType.temporal_change,
            "anomaly": ObservationType.classification,
            "opportunity": ObservationType.classification,
            "risk": ObservationType.classification,
            "contact_info": ObservationType.fact,
            "price": ObservationType.measurement,
            "availability": ObservationType.measurement,
        }

        finding_type_val = (
            finding.finding_type.value
            if hasattr(finding.finding_type, "value")
            else str(finding.finding_type)
        )
        obs_type = type_map.get(finding_type_val, ObservationType.fact)

        resolved_project_id = project_id or finding.project_id

        observation = Observation(
            project_id=resolved_project_id,
            entity_id=None,
            signal_id=None,
            finding_id=finding.id,
            observation_type=obs_type,
            subject=finding.title,
            content=finding.content,
            structured_value=finding.structured_data or {},
            source_type=(
                finding.source_type.value
                if hasattr(finding.source_type, "value") and finding.source_type
                else (str(finding.source_type) if finding.source_type else None)
            ),
            source_url=finding.source_url,
            source_name=finding.source_name,
            confidence=finding.confidence,
        )
        self.db.add(observation)
        self.db.flush()

        # Link back to the finding
        finding.observation_id = observation.id
        self.db.flush()

        return observation
