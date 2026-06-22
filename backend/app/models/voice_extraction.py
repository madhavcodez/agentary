from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import (
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
from .enums import FailureCategory


class VoiceExtractionStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"


class CallDirection(str, enum.Enum):
    outbound = "outbound"
    inbound = "inbound"


class CallStatus(str, enum.Enum):
    pending = "pending"
    ringing = "ringing"
    connected = "connected"
    completed = "completed"
    failed = "failed"
    no_answer = "no_answer"
    voicemail = "voicemail"


class VoiceExtraction(Base):
    __tablename__ = "voice_extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(
        SAEnum(VoiceExtractionStatus), default=VoiceExtractionStatus.draft, nullable=False
    )
    objective = Column(Text)
    persona = Column(JSONB, default=dict)  # {name, role, tone, company_context, opening_script}
    extraction_schema = Column(JSONB, default=dict)  # {fields: [{name, type, question}]}
    call_script_template = Column(Text)
    objection_handlers = Column(JSONB, default=list)
    max_call_duration_seconds = Column(Integer, default=300)
    business_hours_only = Column(Boolean, default=True)
    targets = Column(JSONB, default=list)
    total_targets = Column(Integer, default=0)
    calls_completed = Column(Integer, default=0)
    calls_successful = Column(Integer, default=0)
    data_points_extracted = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project = relationship("Project", back_populates="voice_extractions")
    call_records = relationship("CallRecord", back_populates="voice_extraction", lazy="dynamic")


class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    voice_extraction_id = Column(
        UUID(as_uuid=True), ForeignKey("voice_extractions.id"), nullable=False, index=True
    )
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    phone_number = Column(String(20))
    target_name = Column(String(255))
    target_context = Column(JSONB, default=dict)
    provider_call_id = Column(String(255))
    direction = Column(SAEnum(CallDirection), default=CallDirection.outbound)
    status = Column(SAEnum(CallStatus), default=CallStatus.pending, nullable=False)
    recording_url = Column(String(2048))
    transcript = Column(Text)
    duration_seconds = Column(Integer)
    extracted_data = Column(JSONB, default=dict)
    extraction_confidence = Column(Float)
    extraction_notes = Column(Text)
    sentiment = Column(String(20))
    call_quality_score = Column(Float)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Lifecycle state machine columns
    failure_category = Column(SAEnum(FailureCategory, name="failurecategory"), nullable=True)
    failure_message = Column(Text, nullable=True)
    state_transitions = Column(JSONB, default=list)
    correlation_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Relationships
    voice_extraction = relationship("VoiceExtraction", back_populates="call_records")
