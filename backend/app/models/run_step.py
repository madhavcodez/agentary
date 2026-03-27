"""RunStep model -- records individual execution steps for any run type."""

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
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..database import Base


class StepType(str, enum.Enum):
    expert_task = "expert_task"
    tool_call = "tool_call"
    synthesis = "synthesis"
    node_execution = "node_execution"
    api_call = "api_call"
    signal_processing = "signal_processing"


class RunStep(Base):
    __tablename__ = "run_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    run_type = Column(String(50), nullable=False)  # mission, crew, workflow, voice, monitor, report
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    step_type = Column(SAEnum(StepType), nullable=False)
    step_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="running")

    input_summary = Column(JSONB, default=dict)   # truncated input snapshot
    output_summary = Column(JSONB, default=dict)   # truncated output snapshot
    error = Column(JSONB, nullable=True)

    tokens_used = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    parent_step_id = Column(UUID(as_uuid=True), ForeignKey("run_steps.id"), nullable=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
