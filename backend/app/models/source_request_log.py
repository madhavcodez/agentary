import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..database import Base


class SourceRequestLog(Base):
    __tablename__ = "source_request_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    data_source_id = Column(
        UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False, index=True
    )
    mission_id = Column(UUID(as_uuid=True), nullable=True)
    request_type = Column(String(100), nullable=True)
    request_params = Column(JSONB, nullable=True)
    response_status = Column(Integer, nullable=True)
    response_preview = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
