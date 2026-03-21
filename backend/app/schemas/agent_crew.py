from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentCrewCreate(BaseModel):
    mission_id: UUID
    agents: list | None = None
    coordination_strategy: str = "parallel"


class AgentCrewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    mission_id: UUID
    agents: list | None = None
    coordination_strategy: str
    created_at: datetime


class AgentActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    mission_id: UUID
    run_id: UUID | None = None
    crew_id: UUID | None = None
    expert_agent_id: UUID | None = None
    activity_type: str
    content: str | None = None
    confidence: float | None = None
    created_at: datetime
