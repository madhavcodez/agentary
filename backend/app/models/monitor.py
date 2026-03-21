"""Monitor and Alert models for scheduled checks and notifications."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class MonitorStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class MonitorType(str, enum.Enum):
    web_content = "web_content"
    api_data = "api_data"
    price_tracker = "price_tracker"
    listing_watcher = "listing_watcher"
    competitor_tracker = "competitor_tracker"
    custom = "custom"


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class Monitor(Base):
    __tablename__ = "monitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(SAEnum(MonitorStatus), default=MonitorStatus.active, nullable=False)
    monitor_type = Column(SAEnum(MonitorType), nullable=False)

    check_config = Column(JSONB, default=dict)
    alert_config = Column(JSONB, default=dict)

    schedule_cron = Column(String(100))
    timezone = Column(String(50), default="UTC")

    last_check_at = Column(DateTime(timezone=True))
    last_change_at = Column(DateTime(timezone=True))
    last_snapshot = Column(JSONB)

    total_checks = Column(Integer, default=0)
    total_alerts = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="monitors")
    alerts = relationship("Alert", back_populates="monitor", cascade="all, delete-orphan")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_id = Column(UUID(as_uuid=True), ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)

    alert_type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    message = Column(Text)
    severity = Column(SAEnum(AlertSeverity), default=AlertSeverity.info, nullable=False)
    data = Column(JSONB, default=dict)

    acknowledged = Column(Boolean, default=False, nullable=False)
    acknowledged_at = Column(DateTime(timezone=True))
    acknowledged_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    delivered_channels = Column(ARRAY(String))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    monitor = relationship("Monitor", back_populates="alerts")
