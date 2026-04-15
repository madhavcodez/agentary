"""Contractor report — output of Stream C contractor pipeline.

One row per (pool_listing, pipeline run). Top-ranked quotes are stored
verbatim as JSONB so the UI can render them without re-running the
discovery + voice + verification loop.
"""
from __future__ import annotations

import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class ContractorReportStatus(str, enum.Enum):
    """Lifecycle of a contractor-pipeline run."""

    pending = "pending"
    quoting = "quoting"
    ready = "ready"
    failed = "failed"


class ContractorReport(Base):
    __tablename__ = "contractor_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_listing_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pool_listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(
        SAEnum(ContractorReportStatus, name="contractorreportstatus"),
        nullable=False,
        default=ContractorReportStatus.pending,
    )
    discovery_count = Column(Integer, nullable=False, default=0)
    verified_count = Column(Integer, nullable=False, default=0)
    quote_count = Column(Integer, nullable=False, default=0)
    top_quotes = Column(JSONB, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    pool_listing = relationship("PoolListing")
