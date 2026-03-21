import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID

from ..database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    source_type = Column(String(50), nullable=False)  # api|scraper|database|file|voice|manual
    provider = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSON, default=dict)
    auth_config = Column(JSON, default=dict)
    rate_limit = Column(JSON, default=dict)
    cost_per_request = Column(Float, nullable=True)
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    health_status = Column(String(20), default="unknown")  # healthy|degraded|down|unknown
    last_health_check = Column(DateTime, nullable=True)
    total_requests = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
