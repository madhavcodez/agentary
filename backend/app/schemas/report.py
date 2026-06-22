from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

# ── Request schemas ──────────────────────────────────────────────────


class ReportCreate(BaseModel):
    mission_id: str
    report_type: str = "research_report"
    config: dict[str, Any] | None = None


class ReportUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class RegenerateSection(BaseModel):
    section_index: int
    instructions: str | None = None


# ── Response schemas ─────────────────────────────────────────────────


class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    project_id: str | None = None
    mission_id: str | None = None
    title: str
    description: str | None = None
    report_type: str
    status: str
    share_enabled: bool = False
    created_at: datetime
    updated_at: datetime


class ReportFull(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    project_id: str | None = None
    mission_id: str | None = None
    title: str
    description: str | None = None
    report_type: str
    status: str
    content_markdown: str | None = None
    content_html: str | None = None
    sections: list[dict[str, Any]] | None = None
    executive_summary: str | None = None
    methodology: str | None = None
    sources: list[dict[str, Any]] | None = None
    charts: list[dict[str, Any]] | None = None
    structured_data: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    format_config: dict[str, Any] | None = None
    share_token: str | None = None
    share_enabled: bool = False
    pdf_url: str | None = None
    created_at: datetime
    updated_at: datetime


class ReportList(BaseModel):
    items: list[ReportSummary]
    total: int
    page: int
    limit: int


class ShareResponse(BaseModel):
    url: str
    token: str
