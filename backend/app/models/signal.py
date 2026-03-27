from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class SignalSourceType(str, enum.Enum):
    monitor = "monitor"
    mission = "mission"
    workflow = "workflow"
    voice = "voice"
    user = "user"
    api = "api"
    upload = "upload"
    action_outcome = "action_outcome"


class SignalType(str, enum.Enum):
    change_detected = "change_detected"
    data_extracted = "data_extracted"
    threshold_breached = "threshold_breached"
    pattern_found = "pattern_found"
    anomaly_detected = "anomaly_detected"
    user_flagged = "user_flagged"


class Signal(Base):
    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    source_type = Column(SAEnum(SignalSourceType), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    signal_type = Column(SAEnum(SignalType), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    structured_data = Column(JSONB, default=dict)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    is_processed = Column(Boolean, default=False, nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")
    entity = relationship("Entity", back_populates="signals")
    observations = relationship("Observation", back_populates="signal")
