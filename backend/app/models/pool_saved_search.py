"""Saved Pool Concierge searches for recurring (cron-driven) digests.

Each row represents a user's standing request: "run the Pool Concierge
pipeline for this ZIP every morning with these budget bounds". The
OpenClaw cron (or an equivalent scheduler) iterates enabled rows and
POSTs ``/api/verticals/pool/run`` for each.
"""
from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class PoolSavedSearch(Base):
    """A user's standing search criteria for the Pool Concierge vertical."""

    __tablename__ = "pool_saved_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zipcode = Column(String(10), nullable=False)
    radius_mi = Column(Float, nullable=False, default=5.0)
    max_budget = Column(Integer, nullable=True)
    min_budget = Column(Integer, nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User")
