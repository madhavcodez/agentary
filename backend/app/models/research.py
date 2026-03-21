from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ..database import Base


class ResearchResult(Base):
    __tablename__ = "research_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    match_id = Column(UUID(as_uuid=True), ForeignKey("matches.id"), nullable=False, index=True)
    company_intel = Column(JSONB, default=dict)
    contacts_found = Column(JSONB, default=list)
    sources_used = Column(JSONB, default=list)
    quality_score = Column(Float, default=0.0)
    researched_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
