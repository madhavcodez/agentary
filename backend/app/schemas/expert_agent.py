from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExpertAgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slug: str
    name: str
    description: str | None = None
    specialty: str
    system_prompt: str | None = None
    tools: list | None = None
    icon: str | None = None
    color: str | None = None
    is_system: bool
    is_active: bool
    created_at: datetime
