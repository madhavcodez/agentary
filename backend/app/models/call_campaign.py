import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class CallCampaign(Base):
    __tablename__ = "call_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    match_id = Column(
        UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False
    )
    contact_id = Column(
        UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=False
    )
    status = Column(String(50), default="pending")
    scheduled_at = Column(DateTime, nullable=True)
    priority = Column(Integer, default=0)
    script_json = Column(JSON, nullable=True)
    max_attempts = Column(Integer, default=3)
    attempt_count = Column(Integer, default=0)

    # Multi-channel outreach fields
    resend_email_id = Column(String(100), nullable=True, index=True)
    email_subject = Column(String(500), nullable=True)
    email_draft = Column(Text, nullable=True)
    email_sent_at = Column(DateTime, nullable=True)
    linkedin_msg = Column(Text, nullable=True)
    linkedin_sent_at = Column(DateTime, nullable=True)
    outreach_sequence = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    match = relationship("Match")
    contact = relationship("Contact")
    call_logs = relationship(
        "CallLog", back_populates="campaign", cascade="all, delete-orphan"
    )
