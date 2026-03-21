from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceCreate(BaseModel):
    name: str
    source_type: str
    adapter_slug: str | None = None
    config: dict | None = None
    rate_limit: dict | None = None


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID | None = None
    name: str
    source_type: str
    adapter_slug: str | None = None
    config: dict | None = None
    rate_limit: dict | None = None
    is_active: bool
    is_system: bool
    created_at: datetime
