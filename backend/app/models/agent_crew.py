from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class CoordinationStrategy(str, enum.Enum):
    parallel = "parallel"
    sequential = "sequential"
    hierarchical = "hierarchical"


class ActivityType(str, enum.Enum):
    thinking = "thinking"
    searching = "searching"
    scraping = "scraping"
    calling = "calling"
    analyzing = "analyzing"
    writing = "writing"
    found_data = "found_data"
    found_insight = "found_insight"
    error = "error"
    delegating = "delegating"
    synthesizing = "synthesizing"


class AgentCrew(Base):
    __tablename__ = "agent_crews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=False, index=True)
    agents = Column(JSONB, default=list)  # [{agent_id, role, config_overrides}]
    coordination_strategy = Column(SAEnum(CoordinationStrategy), default=CoordinationStrategy.parallel)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    mission = relationship("Mission", back_populates="crew")
    activities = relationship("AgentActivity", back_populates="crew", lazy="dynamic")
    # Runs are accessed via MissionRun.mission_id -> Mission.crew


class AgentActivity(Base):
    __tablename__ = "agent_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=False, index=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("mission_runs.id"), nullable=True, index=True)
    crew_id = Column(UUID(as_uuid=True), ForeignKey("agent_crews.id"), nullable=True, index=True)
    expert_agent_id = Column(UUID(as_uuid=True), ForeignKey("expert_agents.id"), nullable=True)
    activity_type = Column(SAEnum(ActivityType), nullable=False)
    content = Column(Text)
    metadata_json = Column("metadata", JSONB, default=dict)
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    crew = relationship("AgentCrew", back_populates="activities")
    expert_agent = relationship("ExpertAgent")
