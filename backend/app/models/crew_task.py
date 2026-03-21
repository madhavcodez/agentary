import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class CrewTask(Base):
    __tablename__ = "crew_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(
        UUID(as_uuid=True), ForeignKey("crew_runs.id"), nullable=False, index=True
    )
    expert_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("expert_agents.id"), nullable=False, index=True
    )
    task_type = Column(
        String(50), nullable=False
    )  # web_search|api_query|voice_call|data_analysis|synthesis|report_writing|entity_extraction|comparison|trend_analysis|fact_verification
    description = Column(Text, nullable=False)
    input_data = Column(JSONB, default=dict)
    status = Column(
        String(50), nullable=False, default="pending"
    )  # pending|running|completed|failed|skipped
    thinking_log = Column(
        JSONB, default=list
    )  # array of {timestamp, thought, action, tool, result_preview} — LIVE DASHBOARD SHOWS THIS
    output_data = Column(JSONB, nullable=True)
    findings_produced = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    retry_count = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    run = relationship("CrewRun", back_populates="tasks")
    expert_agent = relationship("ExpertAgent", back_populates="crew_tasks")
