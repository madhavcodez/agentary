from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class MissionStatus(str, enum.Enum):
    draft = "draft"
    queued = "queued"
    running = "running"
    paused = "paused"
    completed = "completed"
    failed = "failed"


class MissionType(str, enum.Enum):
    research = "research"
    voice_extraction = "voice_extraction"
    monitoring = "monitoring"
    data_collection = "data_collection"
    competitive_analysis = "competitive_analysis"
    custom = "custom"


class Mission(Base):
    __tablename__ = "missions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    objective = Column(Text)
    status = Column(SAEnum(MissionStatus), default=MissionStatus.draft, nullable=False)
    mission_type = Column(SAEnum(MissionType), default=MissionType.research, nullable=False)
    instructions = Column(Text)
    parameters = Column(JSONB, default=dict)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=True)
    crew_config = Column(JSONB, default=dict)
    schedule_cron = Column(String(100))
    timezone = Column(String(50), default="UTC")
    summary = Column(Text)
    findings_count = Column(Integer, default=0)
    confidence_score = Column(Float)
    # Per-mission STORM override. NULL = follow global AGENTARY_STORM_ENABLED.
    storm_enabled = Column(Boolean, nullable=True)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="missions")
    crew = relationship("AgentCrew", back_populates="mission", uselist=False)
    findings = relationship("Finding", back_populates="mission", lazy="dynamic")
    runs = relationship("MissionRun", back_populates="mission", lazy="dynamic")
