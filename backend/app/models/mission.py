import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Mission(Base):
    __tablename__ = "missions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    objective = Column(Text, nullable=True)
    scope = Column(JSONB, default=dict)  # geography, time_range, depth, budget_limit
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending|planning|in_progress|completed|failed|cancelled
    required_experts = Column(ARRAY(String), nullable=True)  # slugs or null for auto
    max_experts = Column(Integer, nullable=False, default=5)
    priority = Column(String(20), nullable=False, default="normal")
    schedule_cron = Column(String(100), nullable=True)
    is_recurring = Column(Boolean, nullable=False, default=False)
    summary = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    findings_count = Column(Integer, nullable=False, default=0)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="missions")
    user = relationship("User", backref="missions")
    crew_runs = relationship("CrewRun", back_populates="mission", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="mission", cascade="all, delete-orphan")
    mission_research_results = relationship(
        "MissionResearchResult", back_populates="mission", cascade="all, delete-orphan"
    )
    crews = relationship("AgentCrew", back_populates="mission", cascade="all, delete-orphan")
