from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ── Action Request ──────────────────────────────────────────────────


class ActionRequestCreate(BaseModel):
    project_id: UUID
    action_type: str
    title: str
    description: str | None = None
    parameters: dict | None = None
    recommendation_id: UUID | None = None
    entity_id: UUID | None = None
    confidence: float | None = 1.0
    priority: str | None = "medium"


class ActionRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    recommendation_id: UUID | None = None
    entity_id: UUID | None = None
    user_id: UUID
    action_type: str
    title: str
    description: str | None = None
    parameters: dict | None = None
    confidence: float
    priority: str
    requires_approval: bool
    status: str
    state_transitions: list | None = None
    policy_id: UUID | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime


class ActionApprove(BaseModel):
    note: str | None = None


class ActionReject(BaseModel):
    reason: str


# ── Action Policy ───────────────────────────────────────────────────


class ActionPolicyCreate(BaseModel):
    name: str
    description: str | None = None
    rules: list[dict]
    project_id: UUID | None = None
    priority: int = 0


class ActionPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    project_id: UUID | None = None
    name: str
    description: str | None = None
    rules: list[dict]
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime


# ── Action Execution ────────────────────────────────────────────────


class ActionExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_request_id: UUID
    executor_type: str
    status: str
    result: dict | None = None
    error: dict | None = None
    side_effects: list | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


# ── Action Outcome ──────────────────────────────────────────────────


class ActionOutcomeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    action_request_id: UUID
    execution_id: UUID | None = None
    outcome_type: str
    impact: dict | None = None
    feedback_signal_id: UUID | None = None
    notes: str | None = None
    created_at: datetime


# ── Policy Decision ─────────────────────────────────────────────────


class PolicyDecision(BaseModel):
    requires_approval: bool
    auto_approve: bool
    policy_id: str | None = None
    timeout_hours: int | None = None
