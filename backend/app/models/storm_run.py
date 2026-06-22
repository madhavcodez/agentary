"""Telemetry row for each STORM pipeline invocation.

One row per crew run that attempted STORM (successful or fallback).
Used to answer operational questions — "how many calls did that mission
cost?", "which missions fell back to legacy?" — without having to
reconstruct them from logs.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class StormRun(Base):
    __tablename__ = "storm_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crew_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("crew_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    outline_id = Column(
        UUID(as_uuid=True),
        ForeignKey("research_outlines.id", ondelete="SET NULL"),
        nullable=True,
    )
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Outcome
    status = Column(String(50), nullable=False)  # "completed" | "fallback" | "error"
    fallback_reason = Column(String(255), nullable=True)

    # Counts
    perspectives_count = Column(Integer, nullable=False, default=0)
    questions_count = Column(Integer, nullable=False, default=0)
    sections_count = Column(Integer, nullable=False, default=0)
    sections_with_evidence = Column(Integer, nullable=False, default=0)
    citations_count = Column(Integer, nullable=False, default=0)
    refinement_passes = Column(Integer, nullable=False, default=0)

    # Gemini usage
    flash_calls = Column(Integer, nullable=False, default=0)
    pro_calls = Column(Integer, nullable=False, default=0)

    # Timing
    duration_ms = Column(Integer, nullable=True)

    # Free-form metadata
    meta = Column(JSONB, nullable=False, default=dict)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    mission = relationship("Mission")
