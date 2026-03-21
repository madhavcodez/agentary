import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mission_id = Column(
        UUID(as_uuid=True), ForeignKey("missions.id"), nullable=False, index=True
    )
    crew_task_id = Column(
        UUID(as_uuid=True), ForeignKey("crew_tasks.id"), nullable=True, index=True
    )
    expert_agent_id = Column(
        UUID(as_uuid=True), ForeignKey("expert_agents.id"), nullable=True
    )
    voice_session_id = Column(
        UUID(as_uuid=True), ForeignKey("voice_sessions.id"), nullable=True, index=True
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    category = Column(
        String(50), nullable=False, default="data_point"
    )  # data_point|insight|trend|risk|opportunity|fact|quote|statistic|comparison
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    structured_data = Column(JSONB, nullable=True)
    source_type = Column(
        String(50), nullable=True
    )  # web|api|voice_call|calculation|inference
    source_url = Column(Text, nullable=True)
    source_name = Column(String(255), nullable=True)
    source_raw = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.5)
    verified = Column(Boolean, nullable=False, default=False)
    verification_sources = Column(JSONB, nullable=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    tags = Column(ARRAY(String), default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    mission = relationship("Mission", back_populates="findings")
    crew_task = relationship("CrewTask", backref="findings")
    expert_agent = relationship("ExpertAgent", backref="findings")
