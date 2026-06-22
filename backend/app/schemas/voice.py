"""Pydantic schemas for voice extraction API routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Voice Extraction (campaign/batch)
# ---------------------------------------------------------------------------


class VoiceExtractionCreate(BaseModel):
    project_id: UUID
    mission_id: UUID | None = None
    name: str
    description: str | None = None
    objective: str | None = None
    persona: dict[str, Any] | None = None
    extraction_schema: dict[str, Any] | None = None
    call_script_template: str | None = None
    objection_handlers: list[dict[str, Any]] | None = None
    max_call_duration_seconds: int = 300
    business_hours_only: bool = True
    targets: list[dict[str, Any]] | None = None
    template_name: str | None = None  # Use a built-in template


class VoiceExtractionResponse(BaseModel):
    id: UUID
    project_id: UUID
    mission_id: UUID | None = None
    name: str
    description: str | None = None
    status: str
    objective: str | None = None
    persona: dict[str, Any] | None = None
    extraction_schema: dict[str, Any] | None = None
    total_targets: int
    calls_completed: int
    calls_successful: int
    data_points_extracted: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VoiceExtractionList(BaseModel):
    items: list[VoiceExtractionResponse]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# Call Record
# ---------------------------------------------------------------------------


class CallRecordCreate(BaseModel):
    phone_number: str
    target_name: str
    target_context: dict[str, Any] | None = None


class CallRecordResponse(BaseModel):
    id: UUID
    voice_extraction_id: UUID
    phone_number: str | None = None
    target_name: str | None = None
    target_context: dict[str, Any] | None = None
    provider_call_id: str | None = None
    direction: str | None = None
    status: str
    recording_url: str | None = None
    transcript: str | None = None
    duration_seconds: int | None = None
    extracted_data: dict[str, Any] | None = None
    extraction_confidence: float | None = None
    extraction_notes: str | None = None
    sentiment: str | None = None
    call_quality_score: float | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CallRecordList(BaseModel):
    items: list[CallRecordResponse]
    total: int


# ---------------------------------------------------------------------------
# Batch Operations
# ---------------------------------------------------------------------------


class BatchCallRequest(BaseModel):
    voice_extraction_id: UUID
    targets: list[CallRecordCreate]


class BatchCallResponse(BaseModel):
    voice_extraction_id: UUID
    total: int
    planned: int
    call_record_ids: list[UUID]


class BatchStatusResponse(BaseModel):
    voice_extraction_id: UUID
    status: str
    total_targets: int
    calls_completed: int
    calls_successful: int
    data_points_extracted: int
    call_statuses: dict[str, int]
    records: list[dict[str, Any]]


class BatchResultsResponse(BaseModel):
    voice_extraction_id: UUID
    total: int
    completed: int
    failed: int
    results: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


class TemplateResponse(BaseModel):
    name: str
    description: str
    category: str
    field_count: int


class TemplateListResponse(BaseModel):
    templates: list[TemplateResponse]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


class ExtractionResultResponse(BaseModel):
    fields: list[dict[str, Any]]
    overall_confidence: float
    quality_score: float


class ReextractRequest(BaseModel):
    pass  # No body needed — re-runs extraction on existing transcript
