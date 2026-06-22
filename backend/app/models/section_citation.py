"""Per-section citation binding for STORM-generated reports.

Makes the "section-level citation grounding" claim structurally real:
every citation is a row with FK to ``findings`` and a pointer to the
specific ``section_index`` it supports. Interviewers (or auditors) can
answer "show me the evidence for section 3 of report X" with a SELECT.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class SectionCitation(Base):
    __tablename__ = "section_citations"
    __table_args__ = (Index("ix_section_citations_report_section", "report_id", "section_index"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    section_index = Column(Integer, nullable=False)
    finding_id = Column(
        UUID(as_uuid=True),
        ForeignKey("findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quote_span = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    report = relationship("Report")
    finding = relationship("Finding")
