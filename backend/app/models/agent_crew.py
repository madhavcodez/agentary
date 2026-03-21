import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class AgentCrew(Base):
    __tablename__ = "agent_crews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(
        UUID(as_uuid=True), ForeignKey("missions.id"), nullable=False, index=True
    )
    name = Column(String(255), nullable=False)
    expert_agent_ids = Column(ARRAY(UUID(as_uuid=True)), default=list)
    lead_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("expert_agents.id"), nullable=True
    )
    collaboration_mode = Column(
        String(50), nullable=False, default="parallel"
    )  # parallel|sequential|hierarchical
    max_iterations = Column(Integer, nullable=False, default=3)
    time_limit_seconds = Column(Integer, nullable=False, default=3600)
    status = Column(
        String(50), nullable=False, default="assembled"
    )  # assembled|running|completed|failed
    created_at = Column(DateTime, default=datetime.utcnow)

    mission = relationship("Mission", back_populates="crews")
    lead_agent = relationship("ExpertAgent", foreign_keys=[lead_agent_id])
    runs = relationship("CrewRun", back_populates="crew", cascade="all, delete-orphan")
