from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

from ..database import Base


class AgentSpecialty(str, enum.Enum):
    web_researcher = "web_researcher"
    data_extractor = "data_extractor"
    voice_caller = "voice_caller"
    market_analyst = "market_analyst"
    financial_analyst = "financial_analyst"
    real_estate_expert = "real_estate_expert"
    competitive_intel = "competitive_intel"
    due_diligence = "due_diligence"
    synthesizer = "synthesizer"
    local_business_intel = "local_business_intel"


class ExpertAgent(Base):
    __tablename__ = "expert_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    specialty = Column(SAEnum(AgentSpecialty), nullable=False)
    system_prompt = Column(Text)
    tools = Column(JSONB, default=list)
    model_config_json = Column("model_config", JSONB, default=dict)
    icon = Column(String(50))
    color = Column(String(7))
    is_system = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
