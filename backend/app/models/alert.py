"""Standalone Alert model for richer alert management."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class AlertType(str, enum.Enum):
    change_detected = "change_detected"
    threshold_exceeded = "threshold_exceeded"
    new_data = "new_data"
    error = "error"


class AlertSeverityLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    alert_type = Column(SAEnum(AlertType), nullable=False)
    severity = Column(SAEnum(AlertSeverityLevel), default=AlertSeverityLevel.low, nullable=False)

    title = Column(String(500), nullable=False)
    message = Column(Text)
    data = Column(JSONB, default=dict)

    is_read = Column(Boolean, default=False, nullable=False)
    read_at = Column(DateTime(timezone=True), nullable=True)

    notification_sent = Column(Boolean, default=False, nullable=False)
    notification_channels = Column(JSONB, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    monitor = relationship("Monitor")
    project = relationship("Project")
