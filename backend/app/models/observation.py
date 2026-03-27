from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class ObservationType(str, enum.Enum):
    fact = "fact"
    measurement = "measurement"
    quote = "quote"
    classification = "classification"
    comparison = "comparison"
    temporal_change = "temporal_change"
    relationship_observed = "relationship"


class Observation(Base):
    __tablename__ = "observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=True, index=True)
    signal_id = Column(UUID(as_uuid=True), ForeignKey("signals.id"), nullable=True, index=True)
    finding_id = Column(UUID(as_uuid=True), ForeignKey("findings.id"), nullable=True, index=True)
    run_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    observation_type = Column(SAEnum(ObservationType), nullable=False)
    subject = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    structured_value = Column(JSONB, default=dict)
    source_type = Column(String(50), nullable=True)
    source_url = Column(String(2048), nullable=True)
    source_name = Column(String(255), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=True)
    confidence = Column(Float, nullable=True)
    is_stale = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")
    entity = relationship("Entity", back_populates="observations")
    signal = relationship("Signal", back_populates="observations")
    evidence_links = relationship("Evidence", back_populates="observation")
