from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class EvidenceType(str, enum.Enum):
    supporting = "supporting"
    contradicting = "contradicting"
    contextual = "contextual"


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    observation_id = Column(UUID(as_uuid=True), ForeignKey("observations.id"), nullable=False, index=True)
    insight_id = Column(UUID(as_uuid=True), ForeignKey("insights.id"), nullable=True, index=True)
    recommendation_id = Column(UUID(as_uuid=True), ForeignKey("recommendations.id"), nullable=True, index=True)
    evidence_type = Column(SAEnum(EvidenceType), nullable=False, default=EvidenceType.supporting)
    weight = Column(Float, default=1.0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    observation = relationship("Observation", back_populates="evidence_links")
    insight = relationship("Insight", back_populates="evidence_links")
    recommendation = relationship("Recommendation", back_populates="evidence_links")
