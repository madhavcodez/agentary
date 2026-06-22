from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

# ── Signal ───────────────────────────────────────────────────────────

class SignalCreate(BaseModel):
    project_id: UUID
    source_type: str = "user"
    signal_type: str = "user_flagged"
    title: str
    content: str | None = None
    structured_data: dict | None = None
    source_id: UUID | None = None
    entity_id: UUID | None = None
    confidence: float | None = None


class SignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: UUID
    source_type: str
    source_id: UUID | None = None
    signal_type: str
    title: str
    content: str | None = None
    structured_data: dict | None = None
    entity_id: UUID | None = None
    confidence: float | None = None
    is_processed: bool
    content_hash: str | None = None
    expires_at: datetime | None = None
    created_at: datetime


# ── Observation ──────────────────────────────────────────────────────

class ObservationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    entity_id: UUID | None = None
    signal_id: UUID | None = None
    finding_id: UUID | None = None
    run_id: UUID | None = None
    observation_type: str
    subject: str
    content: str | None = None
    structured_value: dict | None = None
    source_type: str | None = None
    source_url: str | None = None
    source_name: str | None = None
    observed_at: datetime | None = None
    confidence: float | None = None
    is_stale: bool
    created_at: datetime


# ── Evidence ─────────────────────────────────────────────────────────

class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    observation_id: UUID
    insight_id: UUID | None = None
    recommendation_id: UUID | None = None
    evidence_type: str
    weight: float
    notes: str | None = None
    created_at: datetime


# ── Insight ──────────────────────────────────────────────────────────

class InsightResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    entity_id: UUID | None = None
    insight_type: str
    title: str
    content: str | None = None
    structured_data: dict | None = None
    confidence: float | None = None
    freshness_at: datetime
    staleness_threshold_hours: int
    is_stale: bool
    is_active: bool
    superseded_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    evidence_links: list[EvidenceResponse] = []


# ── Recommendation ───────────────────────────────────────────────────

class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    entity_id: UUID | None = None
    insight_id: UUID | None = None
    recommendation_type: str
    title: str
    rationale: str | None = None
    suggested_action: dict | None = None
    confidence: float | None = None
    priority: str
    status: str
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    rejection_reason: str | None = None
    expires_at: datetime | None = None
    created_at: datetime
    evidence_links: list[EvidenceResponse] = []


class RecommendationUpdate(BaseModel):
    rejection_reason: str | None = None


# ── Entity Alias ─────────────────────────────────────────────────────

class EntityAliasCreate(BaseModel):
    alias_type: str
    alias_value: str
    source_name: str | None = None
    confidence: float = 1.0


class EntityAliasResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_id: UUID
    alias_type: str
    alias_value: str
    source_name: str | None = None
    confidence: float
    created_at: datetime


# ── Entity Relationship ──────────────────────────────────────────────

class EntityRelationshipCreate(BaseModel):
    project_id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    properties: dict | None = None
    confidence: float = 1.0
    source_id: UUID | None = None


class EntityRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    relationship_type: str
    properties: dict | None = None
    confidence: float
    source_id: UUID | None = None
    created_at: datetime
