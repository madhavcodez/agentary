from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class RecommendationType(str, enum.Enum):
    investigate = "investigate"
    monitor = "monitor"
    contact = "contact"
    update = "update"
    review = "review"
    escalate = "escalate"


class RecommendationPriority(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class RecommendationStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"
    acted_on = "acted_on"


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True, index=True)
    insight_id = Column(UUID(as_uuid=True), ForeignKey("insights.id"), nullable=True, index=True)
    recommendation_type = Column(SAEnum(RecommendationType), nullable=False)
    title = Column(String(500), nullable=False)
    rationale = Column(Text, nullable=True)
    suggested_action = Column(JSONB, default=dict)
    confidence = Column(Float, nullable=True)
    priority = Column(SAEnum(RecommendationPriority), default=RecommendationPriority.medium, nullable=False)
    status = Column(SAEnum(RecommendationStatus), default=RecommendationStatus.pending, nullable=False)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")
    entity = relationship("Entity", back_populates="recommendations")
    insight = relationship("Insight", back_populates="recommendations")
    evidence_links = relationship("Evidence", back_populates="recommendation")
