from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PolicyCreate(BaseModel):
    name: str
    rules_json: dict | list
    description: str | None = None
    is_active: bool = True


class PolicyUpdate(BaseModel):
    name: str | None = None
    rules_json: dict | list | None = None
    description: str | None = None
    is_active: bool | None = None


class PolicyResponse(BaseModel):
    id: UUID
    name: str
    rules_json: dict | list
    is_active: bool
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
