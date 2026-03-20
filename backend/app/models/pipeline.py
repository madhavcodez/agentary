"""Pipeline stage model and transition tracking.

Tracks the CRM pipeline stage for each match and records
every transition with its trigger for audit and analytics.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class PipelineStage(str, enum.Enum):
    LEAD = "lead"
    CONTACTED = "contacted"
    AWARE = "aware"
    ENGAGED = "engaged"
    MEETING = "meeting"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"
    PAUSED = "paused"


STAGE_ORDER: dict[PipelineStage, int] = {s: i for i, s in enumerate(PipelineStage)}


class PipelineTransition(Base):
    __tablename__ = "pipeline_transitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    match_id = Column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True,
    )
    from_stage = Column(String(20), nullable=False)
    to_stage = Column(String(20), nullable=False)
    trigger = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
