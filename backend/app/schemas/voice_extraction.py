from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VoiceExtractionCreate(BaseModel):
    project_id: UUID
    mission_id: UUID | None = None
    name: str
    description: str | None = None
    objective: str | None = None
    persona: dict | None = None
    extraction_schema: dict | None = None
    call_script_template: str | None = None
    objection_handlers: list | None = None
    max_call_duration_seconds: int = 300
    business_hours_only: bool = True
    targets: list | None = None


class VoiceExtractionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    objective: str | None = None
    persona: dict | None = None
    extraction_schema: dict | None = None
    call_script_template: str | None = None
    targets: list | None = None


class VoiceExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    mission_id: UUID | None = None
    name: str
    description: str | None = None
    status: str
    objective: str | None = None
    persona: dict | None = None
    extraction_schema: dict | None = None
    total_targets: int
    calls_completed: int
    calls_successful: int
    data_points_extracted: int
    created_at: datetime
    updated_at: datetime


class CallRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    voice_extraction_id: UUID
    phone_number: str | None = None
    target_name: str | None = None
    direction: str
    status: str
    transcript: str | None = None
    duration_seconds: int | None = None
    extracted_data: dict | None = None
    extraction_confidence: float | None = None
    sentiment: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime
