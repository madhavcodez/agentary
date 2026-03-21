import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    source_type = Column(String(50), nullable=False, default="api")
    provider = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSONB, default=dict)
    auth_config = Column(JSONB, default=dict)
    rate_limit = Column(JSONB, default=dict)
    cost_per_request = Column(Float, nullable=True)
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    health_status = Column(String(20), default="unknown")
    last_health_check = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
