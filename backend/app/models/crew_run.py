import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class CrewRun(Base):
    __tablename__ = "crew_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crew_id = Column(
        UUID(as_uuid=True), ForeignKey("agent_crews.id"), nullable=False, index=True
    )
    mission_id = Column(
        UUID(as_uuid=True), ForeignKey("missions.id"), nullable=False, index=True
    )
    status = Column(
        String(50), nullable=False, default="queued"
    )  # queued|running|completed|failed|cancelled
    trigger_type = Column(
        String(50), nullable=False, default="manual"
    )  # manual|scheduled|monitor_triggered
    iteration = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    metrics = Column(
        JSONB, default=dict
    )  # findings_count, sources_queried, voice_calls_made, tokens_used, cost_usd
    error = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    crew = relationship("AgentCrew", back_populates="runs")
    mission = relationship("Mission", back_populates="crew_runs")
    tasks = relationship("CrewTask", back_populates="run", cascade="all, delete-orphan")
    mission_research_results = relationship(
        "MissionResearchResult", back_populates="crew_run"
    )
