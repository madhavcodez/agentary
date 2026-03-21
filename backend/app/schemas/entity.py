from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EntityCreate(BaseModel):
    project_id: UUID | None = None
    entity_type: str = "other"
    name: str
    description: str | None = None
    properties: dict | None = None
    tags: list | None = None
    source_ids: list | None = None
    confidence_score: float | None = None
    embedding_id: str | None = None


class EntityUpdate(BaseModel):
    entity_type: str | None = None
    name: str | None = None
    description: str | None = None
    properties: dict | None = None
    tags: list | None = None
    source_ids: list | None = None
    confidence_score: float | None = None
    embedding_id: str | None = None
    is_verified: bool | None = None


class EntityMergeRequest(BaseModel):
    source_entity_id: UUID
    target_entity_id: UUID
    strategy: str = "keep_target"  # keep_target, keep_source, merge_all


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    project_id: UUID | None = None
    entity_type: str
    name: str
    description: str | None = None
    properties: dict | None = None
    tags: list | None = None
    source_ids: list | None = None
    confidence_score: float | None = None
    embedding_id: str | None = None
    is_verified: bool
    created_at: datetime
    updated_at: datetime
