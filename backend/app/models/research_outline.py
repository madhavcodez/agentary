"""Persisted pre-writing artifact for STORM-enabled missions.

One row per (mission, version). Stores the mined perspectives, the
question matrix, the section skeleton, and a metadata bag for
budget/telemetry. Bind readers: ``section_synthesizer`` and
``evidence_binder`` read ``sections`` and ``question_matrix``.
"""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class ResearchOutline(Base):
    __tablename__ = "research_outlines"
    __table_args__ = (
        UniqueConstraint("mission_id", "version", name="uq_research_outlines_mission_version"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(
        UUID(as_uuid=True),
        ForeignKey("missions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    perspectives = Column(JSONB, nullable=False, default=list)
    question_matrix = Column(JSONB, nullable=False, default=list)
    sections = Column(JSONB, nullable=False, default=list)
    meta = Column(JSONB, nullable=False, default=dict)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    mission = relationship("Mission")
