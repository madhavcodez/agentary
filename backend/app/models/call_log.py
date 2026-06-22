from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    campaign_id = Column(
        UUID(as_uuid=True), ForeignKey("call_campaigns.id"), nullable=True, index=True
    )
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True)

    twilio_call_sid = Column(String(255), nullable=True, index=True)
    outcome = Column(String(50), nullable=True)
    duration_sec = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
