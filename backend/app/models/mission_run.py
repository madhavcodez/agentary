from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TriggerType(str, enum.Enum):
    manual = "manual"
    scheduled = "scheduled"
    monitor_triggered = "monitor_triggered"


class TaskType(str, enum.Enum):
    discover = "discover"
    research = "research"
    extract = "extract"
    call = "call"
    analyze = "analyze"
    synthesize = "synthesize"
    report = "report"
    monitor_check = "monitor_check"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class MissionRun(Base):
    __tablename__ = "mission_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=False, index=True)
    status = Column(SAEnum(RunStatus), default=RunStatus.queued, nullable=False)
    trigger_type = Column(SAEnum(TriggerType), default=TriggerType.manual, nullable=False)
    config_snapshot = Column(JSONB, default=dict)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    summary = Column(Text)
    metrics = Column(JSONB, default=dict)  # sources_queried, findings_count, calls_made, etc.
    error = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    mission = relationship("Mission", back_populates="runs")
    tasks = relationship("CrewTask", foreign_keys="CrewTask.mission_run_id", lazy="select")


class MissionTask(Base):
    __tablename__ = "mission_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("mission_runs.id"), nullable=False, index=True)
    expert_agent_id = Column(UUID(as_uuid=True), ForeignKey("expert_agents.id"), nullable=True)
    task_type = Column(SAEnum(TaskType), nullable=False)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.pending, nullable=False)
    input_data = Column(JSONB, default=dict)
    result_data = Column(JSONB, default=dict)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    run = relationship("MissionRun")
