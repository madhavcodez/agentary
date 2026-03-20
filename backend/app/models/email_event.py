"""Email event tracking model.

Stores webhook events from Resend (delivered, opened, clicked,
bounced, complained) to provide email intelligence and analytics.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID

from ..database import Base


class EmailEvent(Base):
    __tablename__ = "email_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(
        UUID(as_uuid=True), ForeignKey("call_campaigns.id"), nullable=True, index=True,
    )
    resend_email_id = Column(String(100), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
