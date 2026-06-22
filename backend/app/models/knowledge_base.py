from __future__ import annotations

import enum
import uuid

from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..database import Base


class KBDomain(str, enum.Enum):
    real_estate = "real_estate"
    finance = "finance"
    technology = "technology"
    healthcare = "healthcare"
    retail = "retail"
    custom = "custom"


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    domain = Column(SAEnum(KBDomain), default=KBDomain.custom)
    context_text = Column(Text)
    entities = Column(JSONB, default=list)
    terminology = Column(JSONB, default=dict)
    preferences = Column(JSONB, default=dict)
    documents = Column(JSONB, default=list)
    qdrant_collection = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
