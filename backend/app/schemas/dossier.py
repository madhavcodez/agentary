from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class DossierResponse(BaseModel):
    id: UUID
    match_id: UUID
    content_md: str
    sections_json: dict | list | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
