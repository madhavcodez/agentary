from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MissionCreate(BaseModel):
    project_id: UUID
    name: str
    description: str | None = None
    objective: str | None = None
    mission_type: str = "research"
    instructions: str | None = None
    parameters: dict | None = None
    workflow_id: UUID | None = None
    crew_config: dict | None = None
    schedule_cron: str | None = None
    timezone: str = "UTC"


class MissionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    objective: str | None = None
    status: str | None = None
    mission_type: str | None = None
    instructions: str | None = None
    parameters: dict | None = None
    workflow_id: UUID | None = None
    crew_config: dict | None = None
    schedule_cron: str | None = None
    timezone: str | None = None


class MissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    objective: str | None = None
    status: str
    mission_type: str
    instructions: str | None = None
    parameters: dict | None = None
    workflow_id: UUID | None = None
    crew_config: dict | None = None
    schedule_cron: str | None = None
    timezone: str
    summary: str | None = None
    findings_count: int
    confidence_score: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
