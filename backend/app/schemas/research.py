from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResearchSummary(BaseModel):
    match_id: UUID
    company_intel_keys: list[str] = []
    contacts_found_count: int = 0
    quality_score: float = 0.0
    sources_used: list[str] = []


class ResearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    match_id: UUID
    company_intel: dict[str, Any] | None = None
    contacts_found: list[dict[str, Any]] | None = None
    sources_used: list[str] | None = None
    quality_score: float | None = None
    researched_at: datetime | None = None
    created_at: datetime
