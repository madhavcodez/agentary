from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class FindingType(str, enum.Enum):
    fact = "fact"
    data_point = "data_point"
    insight = "insight"
    quote = "quote"
    statistic = "statistic"
    contact_info = "contact_info"
    price = "price"
    availability = "availability"
    sentiment = "sentiment"
    trend = "trend"
    anomaly = "anomaly"
    opportunity = "opportunity"
    risk = "risk"


class SourceType(str, enum.Enum):
    web = "web"
    voice_call = "voice_call"
    api = "api"
    public_record = "public_record"
    user_provided = "user_provided"
    inferred = "inferred"


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    mission_id = Column(UUID(as_uuid=True), ForeignKey("missions.id"), nullable=True, index=True)
    expert_agent_id = Column(UUID(as_uuid=True), ForeignKey("expert_agents.id"), nullable=True)
    call_record_id = Column(
        UUID(as_uuid=True), ForeignKey("call_records.id"), nullable=True, index=True
    )
    finding_type = Column(SAEnum(FindingType), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text)
    structured_data = Column(JSONB, default=dict)
    source_type = Column(SAEnum(SourceType))
    source_url = Column(String(2048))
    source_name = Column(String(255))
    source_metadata = Column(JSONB, default=dict)
    confidence = Column(Float)
    verified = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True), nullable=True)
    contradicts = Column(UUID(as_uuid=True), ForeignKey("findings.id"), nullable=True)
    tags = Column(JSONB, default=list)
    entity_refs = Column(JSONB, default=list)  # [{type, name, id}]
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project", back_populates="findings")
    mission = relationship("Mission", back_populates="findings")
