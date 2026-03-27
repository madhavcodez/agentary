from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class EntityType(str, enum.Enum):
    company = "company"
    person = "person"
    place = "place"
    product = "product"
    organization = "organization"
    other = "other"


class Entity(Base):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)

    entity_type = Column(SAEnum(EntityType), default=EntityType.other, nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    properties = Column(JSONB, default=dict)
    tags = Column(JSONB, default=list)
    source_ids = Column(JSONB, default=list)
    confidence_score = Column(Float, nullable=True)
    embedding_id = Column(String(255), nullable=True)

    is_verified = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")
    aliases = relationship("EntityAlias", back_populates="entity", lazy="dynamic")
    observations = relationship("Observation", back_populates="entity", lazy="dynamic")
    insights = relationship("Insight", back_populates="entity", lazy="dynamic")
    signals = relationship("Signal", back_populates="entity", lazy="dynamic")
    recommendations = relationship("Recommendation", back_populates="entity", lazy="dynamic")
    outgoing_relationships = relationship(
        "EntityRelationship", foreign_keys="EntityRelationship.from_entity_id", lazy="dynamic"
    )
    incoming_relationships = relationship(
        "EntityRelationship", foreign_keys="EntityRelationship.to_entity_id", lazy="dynamic"
    )
