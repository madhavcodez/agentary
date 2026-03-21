from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class EntityCreate(BaseModel):
    entity_type: str
    name: str
    description: str | None = None
    canonical_data: dict[str, Any] = {}
    aliases: list[str] = []
    source_urls: list[str] = []
    tags: list[str] = []


class EntityUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    canonical_data: dict[str, Any] | None = None
    aliases: list[str] | None = None
    source_urls: list[str] | None = None
    tags: list[str] | None = None


class EntityResponse(BaseModel):
    id: UUID
    user_id: UUID
    entity_type: str
    name: str
    description: str | None = None
    canonical_data: dict[str, Any] = {}
    aliases: list[str] = []
    source_urls: list[str] = []
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class EntityMergeRequest(BaseModel):
    entity_ids: list[UUID]
    primary_id: UUID


class EntitySearchParams(BaseModel):
    q: str | None = None
    entity_type: str | None = None
    project_id: UUID | None = None
    limit: int = 50
    offset: int = 0
