from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime, Enum as SAEnum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class AliasType(str, enum.Enum):
    name_variant = "name_variant"
    external_id = "external_id"
    url = "url"
    phone = "phone"
    email = "email"
    address = "address"


class EntityAlias(Base):
    __tablename__ = "entity_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False, index=True)
    alias_type = Column(SAEnum(AliasType), nullable=False)
    alias_value = Column(String(1000), nullable=False)
    source_name = Column(String(255), nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    entity = relationship("Entity", back_populates="aliases")
