import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSON, UUID

from ..database import Base


class Entity(Base):
    __tablename__ = "entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    entity_type = Column(
        String(50), nullable=False
    )  # person|company|property|location|business|product|other
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    canonical_data = Column(JSON, default=dict)
    aliases = Column(ARRAY(String), default=list)
    source_urls = Column(ARRAY(String), default=list)
    tags = Column(ARRAY(String), default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_entities_type_name", "entity_type", "name"),
    )
