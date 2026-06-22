from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class RelationshipType(str, enum.Enum):
    subsidiary_of = "subsidiary_of"
    competitor_of = "competitor_of"
    partner_of = "partner_of"
    located_at = "located_at"
    works_at = "works_at"
    supplies_to = "supplies_to"
    related_to = "related_to"


class EntityRelationship(Base):
    __tablename__ = "entity_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    from_entity_id = Column(
        UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False, index=True
    )
    to_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False, index=True)
    relationship_type = Column(SAEnum(RelationshipType), nullable=False)
    properties = Column(JSONB, default=dict)
    confidence = Column(Float, default=1.0, nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    project = relationship("Project")
    from_entity = relationship("Entity", foreign_keys=[from_entity_id])
    to_entity = relationship("Entity", foreign_keys=[to_entity_id])
