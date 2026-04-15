"""End-to-end Pool Concierge pipeline run tracker.

One row per invocation of ``run_full_pool_pipeline`` — stages are
tracked through a status enum so the UI/Telegram bot can surface
progress. The ``summary`` JSONB column holds the final digest payload
(top-3 listings with score/price/address/preview links) that the
Telegram handler renders.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class PoolPipelineRunStatus(str, enum.Enum):
    """Lifecycle of an end-to-end Pool Concierge pipeline run."""

    pending = "pending"
    discovering = "discovering"
    scoring = "scoring"
    contractor_quoting = "contractor_quoting"
    ready = "ready"
    failed = "failed"


class PoolPipelineRun(Base):
    """Tracks a single end-to-end Pool Concierge pipeline invocation."""

    __tablename__ = "pool_pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zipcode = Column(String(10), nullable=False)
    status = Column(
        SAEnum(PoolPipelineRunStatus, name="poolpipelinerunstatus"),
        nullable=False,
        default=PoolPipelineRunStatus.pending,
    )
    total_listings = Column(Integer, nullable=False, default=0)
    ready_listings = Column(Integer, nullable=False, default=0)
    telegram_message_id = Column(String(64), nullable=True)
    summary = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User")
