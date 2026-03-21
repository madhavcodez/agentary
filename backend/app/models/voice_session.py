import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(
        UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True, index=True
    )
    crew_task_id = Column(
        UUID(as_uuid=True), ForeignKey("crew_tasks.id"), nullable=True, index=True
    )
    batch_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    template_id = Column(
        UUID(as_uuid=True),
        ForeignKey("extraction_templates.id"),
        nullable=True,
        index=True,
    )

    session_type = Column(
        String(50), nullable=False, default="research_extraction"
    )  # research_extraction | screening | survey | custom
    status = Column(
        String(50), nullable=False, default="planned"
    )  # planned | queued | in_progress | connected | completed | failed | no_answer | voicemail

    # Target info
    target_name = Column(String(500), nullable=False)
    target_phone = Column(String(50), nullable=False)
    target_business = Column(String(500), nullable=True)
    target_context = Column(JSON, nullable=True)

    # Call configuration
    persona_config = Column(JSON, nullable=True)
    extraction_goals = Column(JSON, nullable=True)
    call_script = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=True)

    # Twilio / call data
    twilio_call_sid = Column(String(100), nullable=True)
    recording_url = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    transcript_segments = Column(JSON, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Results
    outcome = Column(String(50), nullable=True)
    extracted_data = Column(JSON, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    cost_usd = Column(Float, nullable=True)

    # Timestamps
    started_at = Column(DateTime, nullable=True)
    connected_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    mission = relationship("Mission", backref="voice_sessions")
    crew_task = relationship("CrewTask", backref="voice_sessions")
    template = relationship("ExtractionTemplate", backref="voice_sessions")
    findings = relationship("Finding", backref="voice_session")
