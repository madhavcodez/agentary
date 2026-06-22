from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
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


class CrewTaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class CrewTask(Base):
    __tablename__ = "crew_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_run_id = Column(UUID(as_uuid=True), ForeignKey("mission_runs.id"), nullable=False, index=True)
    expert_agent_id = Column(UUID(as_uuid=True), ForeignKey("expert_agents.id"), nullable=False, index=True)

    task_type = Column(String(100), nullable=False)
    description = Column(Text)
    status = Column(SAEnum(CrewTaskStatus), default=CrewTaskStatus.pending, nullable=False)

    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)

    findings_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)

    thinking_log = Column(JSONB, default=list)
    tool_calls = Column(JSONB, default=list)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    mission_run = relationship("MissionRun")
    expert_agent = relationship("ExpertAgent")
    findings = relationship("Finding", primaryjoin="foreign(Finding.call_record_id)==CrewTask.id", viewonly=True)
