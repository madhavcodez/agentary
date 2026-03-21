from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PolicyCreate(BaseModel):
    name: str
    rules_json: dict[str, Any] | list[Any]
    description: str | None = None
    is_active: bool = True


class PolicyUpdate(BaseModel):
    name: str | None = None
    rules_json: dict[str, Any] | list[Any] | None = None
    description: str | None = None
    is_active: bool | None = None


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    name: str
    rules_json: dict[str, Any] | list[Any]
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
