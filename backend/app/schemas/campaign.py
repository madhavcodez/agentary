from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class CampaignCreate(BaseModel):
    match_id: UUID
    contact_id: UUID
    scheduled_at: datetime | None = None
    priority: int = 0
    max_attempts: int = 3


class CampaignResponse(BaseModel):
    id: UUID
    match_id: UUID
    contact_id: UUID
    status: str
    scheduled_at: datetime | None = None
    priority: int
    script_json: dict[str, Any] | None = None
    max_attempts: int
    attempt_count: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CampaignList(BaseModel):
    items: list[CampaignResponse]
    total: int
    page: int
    limit: int


class CallLogResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    twilio_call_sid: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_sec: int | None = None
    outcome: str | None = None
    person_reached: str | None = None
    transcript: str | None = None
    summary: str | None = None
    recording_url: str | None = None
    next_steps: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
