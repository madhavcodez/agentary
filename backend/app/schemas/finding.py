from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FindingCreate(BaseModel):
    project_id: UUID
    mission_id: UUID | None = None
    expert_agent_id: UUID | None = None
    finding_type: str
    title: str
    content: str | None = None
    structured_data: dict | None = None
    source_type: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    source_metadata: dict | None = None
    confidence: float | None = None
    tags: list | None = None
    entity_refs: list | None = None


class FindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    mission_id: UUID | None = None
    expert_agent_id: UUID | None = None
    finding_type: str
    title: str
    content: str | None = None
    structured_data: dict | None = None
    source_type: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    confidence: float | None = None
    verified: bool
    tags: list | None = None
    entity_refs: list | None = None
    created_at: datetime
