from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class InsightType(str, enum.Enum):
    trend = "trend"
    risk = "risk"
    opportunity = "opportunity"
    anomaly = "anomaly"
    summary = "summary"
    comparison = "comparison"


class Insight(Base):
    __tablename__ = "insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True, index=True)
    insight_type = Column(SAEnum(InsightType), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    structured_data = Column(JSONB, default=dict)
    confidence = Column(Float, nullable=True)
    freshness_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    staleness_threshold_hours = Column(Integer, default=168, nullable=False)
    is_stale = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    superseded_by = Column(UUID(as_uuid=True), ForeignKey("insights.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")
    entity = relationship("Entity", back_populates="insights")
    evidence_links = relationship("Evidence", back_populates="insight")
    recommendations = relationship("Recommendation", back_populates="insight")
