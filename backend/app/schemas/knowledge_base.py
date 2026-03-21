from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str | None = None
    domain: str = "custom"
    context_text: str | None = None
    entities: list | None = None
    terminology: dict | None = None
    preferences: dict | None = None
    documents: list | None = None


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    domain: str | None = None
    context_text: str | None = None
    entities: list | None = None
    terminology: dict | None = None
    preferences: dict | None = None
    documents: list | None = None


class KnowledgeBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    domain: str
    context_text: str | None = None
    entities: list | None = None
    terminology: dict | None = None
    preferences: dict | None = None
    documents: list | None = None
    qdrant_collection: str | None = None
    created_at: datetime
    updated_at: datetime
