from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StageUpdate(BaseModel):
    stage: str
    trigger: str = "manual"


class PipelineSummary(BaseModel):
    lead: int = 0
    contacted: int = 0
    aware: int = 0
    engaged: int = 0
    meeting: int = 0
    closed_won: int = 0
    closed_lost: int = 0
    paused: int = 0


class TransitionResponse(BaseModel):
    id: UUID
    match_id: UUID
    from_stage: str
    to_stage: str
    trigger: str
    created_at: datetime

    model_config = {"from_attributes": True}
