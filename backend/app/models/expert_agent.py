import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class ExpertAgent(Base):
    __tablename__ = "expert_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    avatar_emoji = Column(String(10), nullable=False, default="🤖")
    category = Column(
        String(50), nullable=False, default="research"
    )  # research|analysis|extraction|synthesis|output
    capabilities = Column(ARRAY(String), default=list)
    tools = Column(ARRAY(String), default=list)
    system_prompt = Column(Text, nullable=False)
    model = Column(String(100), nullable=False, default="gemini-2.5-flash")
    temperature = Column(Float, nullable=False, default=0.3)
    max_tokens = Column(Integer, nullable=False, default=8192)
    is_system = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="expert_agents")
    crew_tasks = relationship("CrewTask", back_populates="expert_agent")
