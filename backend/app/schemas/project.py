from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    project_type: str = "custom"
    domain_context: str | None = None
    knowledge_base_id: UUID | None = None
    default_workflow_id: UUID | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    project_type: str | None = None
    domain_context: str | None = None
    knowledge_base_id: UUID | None = None
    default_workflow_id: UUID | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    status: str
    project_type: str
    domain_context: str | None = None
    knowledge_base_id: UUID | None = None
    default_workflow_id: UUID | None = None
    total_missions: int
    total_findings: int
    total_calls_made: int
    total_reports_generated: int
    created_at: datetime
    updated_at: datetime
