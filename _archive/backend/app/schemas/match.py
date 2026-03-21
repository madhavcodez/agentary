from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from .opportunity import OpportunityResponse


class MatchResponse(BaseModel):
    id: UUID
    opportunity_id: UUID
    profile_id: UUID
    hard_filter_pass: str
    semantic_score: float
    llm_score: float
    composite_score: float
    rationale: str | None = None
    status: str
    pipeline_stage: str = "lead"
    stage_changed_at: datetime | None = None
    opportunity: OpportunityResponse | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MatchList(BaseModel):
    items: list[MatchResponse]
    total: int
    page: int
    limit: int


class MatchAction(BaseModel):
    status: str  # approved, rejected, saved
