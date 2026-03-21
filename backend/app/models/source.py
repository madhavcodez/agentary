from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ..database import Base


class SourceKind(str, enum.Enum):
    web_search = "web_search"
    web_scrape = "web_scrape"
    api = "api"
    public_records = "public_records"
    mls = "mls"
    county_records = "county_records"
    voice = "voice"
    rss = "rss"
    social_media = "social_media"
    file_upload = "file_upload"
    database = "database"


class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # null = system source
    name = Column(String(255), nullable=False)
    source_type = Column(SAEnum(SourceKind), nullable=False)
    adapter_slug = Column(String(100))
    config = Column(JSONB, default=dict)
    credentials_ref = Column(JSONB, default=dict)
    rate_limit = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True, nullable=False)
    is_system = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
