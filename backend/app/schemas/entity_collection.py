from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EntityCollectionCreate(BaseModel):
    name: str
    description: str | None = None
    entity_type: str | None = None
    project_id: UUID | None = None


class EntityCollectionResponse(BaseModel):
    id: UUID
    project_id: UUID | None = None
    user_id: UUID
    name: str
    description: str | None = None
    entity_type: str | None = None
    entity_ids: list[UUID] = []
    filters: dict[str, Any] | None = None
    count: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class EntityCollectionAddRemove(BaseModel):
    entity_ids: list[UUID]
