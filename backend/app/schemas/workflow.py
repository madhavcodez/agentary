from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    category: str = "custom"
    is_template: bool = False
    is_public: bool = False
    nodes: list | None = None
    edges: list | None = None
    parameters: list | None = None


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    nodes: list | None = None
    edges: list | None = None
    parameters: list | None = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID | None = None
    name: str
    description: str | None = None
    category: str
    is_template: bool
    is_public: bool
    nodes: list | None = None
    edges: list | None = None
    parameters: list | None = None
    version: int
    created_at: datetime
    updated_at: datetime
