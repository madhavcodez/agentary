"""MonitorRun model — tracks individual monitor check executions."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base
from .enums import FailureCategory, RunStatus


class MonitorRun(Base):
    __tablename__ = "monitor_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("monitors.id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    status = Column(SAEnum(RunStatus, name="runstatus"), default=RunStatus.created, nullable=False)
    failure_category = Column(SAEnum(FailureCategory, name="failurecategory"), nullable=True)
    failure_message = Column(Text, nullable=True)
    state_transitions = Column(JSONB, default=list)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    result = Column(JSONB, default=dict)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=True, index=True)
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    monitor = relationship("Monitor", back_populates="runs")
