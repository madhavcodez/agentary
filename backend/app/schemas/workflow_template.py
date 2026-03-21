from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkflowTemplateCreate(BaseModel):
    slug: str
    name: str
    description: str | None = None
    category: str = "custom"
    icon: str | None = None
    color: str | None = None
    nodes: list | None = None
    edges: list | None = None
    variables: dict | None = None
    is_system: bool = False


class WorkflowTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    icon: str | None = None
    color: str | None = None
    nodes: list | None = None
    edges: list | None = None
    variables: dict | None = None
    is_active: bool | None = None


class WorkflowTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID | None = None
    slug: str
    name: str
    description: str | None = None
    category: str
    icon: str | None = None
    color: str | None = None
    nodes: list | None = None
    edges: list | None = None
    variables: dict | None = None
    is_system: bool
    is_active: bool
    use_count: int
    created_at: datetime
    updated_at: datetime
