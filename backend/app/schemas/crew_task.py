from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CrewTaskCreate(BaseModel):
    mission_run_id: UUID
    expert_agent_id: UUID
    task_type: str
    description: str | None = None
    input_data: dict | None = None


class CrewTaskUpdate(BaseModel):
    status: str | None = None
    output_data: dict | None = None
    findings_count: int | None = None
    error_message: str | None = None
    thinking_log: list | None = None
    tool_calls: list | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None


class CrewTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    mission_run_id: UUID
    expert_agent_id: UUID
    task_type: str
    description: str | None = None
    status: str
    input_data: dict | None = None
    output_data: dict | None = None
    findings_count: int
    error_message: str | None = None
    thinking_log: list | None = None
    tool_calls: list | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    created_at: datetime
    updated_at: datetime
