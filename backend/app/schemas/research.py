from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class ResearchTrigger(BaseModel):
    """Body for triggering research on a match (currently empty; match_id comes from path)."""
    pass


class ResearchResponse(BaseModel):
    id: UUID
    match_id: UUID
    company_intel: dict[str, Any] | None = None
    contacts_found: list[dict[str, Any]] | None = None
    sources_used: list[str] | None = None
    quality_score: float
    researched_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ResearchSummary(BaseModel):
    """Lightweight summary returned after triggering research."""
    match_id: UUID
    company_intel_keys: list[str]
    contacts_found_count: int
    quality_score: float
    sources_used: list[str]


class AutopilotRunResult(BaseModel):
    ingest: int = 0
    scored: int = 0
    researched: int = 0
    campaigns_created: int = 0


class AutopilotStatus(BaseModel):
    last_run: datetime | None = None
    last_result: AutopilotRunResult | None = None
    running: bool = False
