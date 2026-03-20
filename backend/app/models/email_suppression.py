"""Email suppression list model.

Tracks email addresses that should not receive further outreach
due to bounces, complaints, or unsubscribe requests. Checked
before every email send to maintain sender reputation.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from ..database import Base


class EmailSuppression(Base):
    __tablename__ = "email_suppressions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), unique=True, nullable=False, index=True)
    reason = Column(String(50), nullable=False)  # bounced, complained, unsubscribed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
