import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    hard_filter_pass = Column(String(10), default="pending")
    semantic_score = Column(Float, default=0.0)
    llm_score = Column(Float, default=0.0)
    composite_score = Column(Float, default=0.0)
    rationale = Column(Text)
    status = Column(String(50), default="new")
    pipeline_stage = Column(String(20), default="lead", nullable=False, index=True)
    stage_changed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    opportunity = relationship("Opportunity")
    profile = relationship("Profile")
    dossier = relationship("Dossier", back_populates="match", uselist=False)
