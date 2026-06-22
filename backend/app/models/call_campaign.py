from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..database import Base


class CallCampaign(Base):
    __tablename__ = "call_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=True)

    status = Column(String(50), default="pending", nullable=False)
    campaign_type = Column(String(50), default="outbound_call", nullable=False)

    script_json = Column(JSONB, default=dict)
    resend_email_id = Column(String(255), nullable=True)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)

    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)

    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
