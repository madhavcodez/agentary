from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MissionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    mission_id: UUID
    status: str
    trigger_type: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    summary: str | None = None
    metrics: dict | None = None
    error: dict | None = None
    created_at: datetime


class MissionTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    run_id: UUID
    expert_agent_id: UUID | None = None
    task_type: str
    status: str
    result_data: dict | None = None
    error_message: str | None = None
    duration_seconds: float | None = None
    retry_count: int
    created_at: datetime
