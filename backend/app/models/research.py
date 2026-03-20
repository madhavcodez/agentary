import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class ResearchResult(Base):
    __tablename__ = "research_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    match_id = Column(
        UUID(as_uuid=True),
        ForeignKey("matches.id"),
        nullable=False,
        unique=True,
    )
    company_intel = Column(JSON, default=dict)
    contacts_found = Column(JSON, default=list)
    sources_used = Column(JSON, default=list)
    quality_score = Column(Float, default=0.0)
    researched_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    match = relationship("Match", backref="research_result")
