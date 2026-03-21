from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EntityCollectionCreate(BaseModel):
    project_id: UUID | None = None
    name: str
    description: str | None = None
    entity_type: str | None = None
    entity_ids: list[UUID] | None = None
    filters: dict | None = None


class EntityCollectionAddRemove(BaseModel):
    entity_ids: list[UUID]


class EntityCollectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    project_id: UUID | None = None
    name: str
    description: str | None = None
    entity_type: str | None = None
    entity_ids: list[UUID] | None = None
    filters: dict | None = None
    count: int
    created_at: datetime
    updated_at: datetime
