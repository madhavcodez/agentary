from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Node & Edge schemas ──────────────────────────────────────────────

class EdgeSchema(BaseModel):
    source_node_id: str
    target_node_id: str
    source_port: str = "output"
    target_port: str = "input"


class NodeSchema(BaseModel):
    id: str
    type: str
    label: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})


# ── Variable schema ──────────────────────────────────────────────────

class VariableSchema(BaseModel):
    name: str
    type: str = "string"
    label: str = ""
    required: bool = False
    default: Any = None
    description: str = ""


# ── Workflow CRUD ────────────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = None
    project_id: UUID | None = None
    status: str = "draft"
    trigger_type: str = "manual"
    trigger_config: dict[str, Any] | None = None
    created_from: str = "visual_editor"
    template_id: UUID | None = None
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    variables: dict[str, Any] = Field(default_factory=dict)


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    trigger_type: str | None = None
    trigger_config: dict[str, Any] | None = None
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None
    variables: dict[str, Any] | None = None


class WorkflowResponse(BaseModel):
    id: UUID
    project_id: UUID | None = None
    user_id: UUID
    name: str
    description: str | None = None
    status: str
    trigger_type: str
    trigger_config: dict[str, Any] | None = None
    created_from: str
    template_id: UUID | None = None
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    variables: dict[str, Any]
    last_run_at: datetime | None = None
    total_runs: int
    avg_duration_seconds: float | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class WorkflowList(BaseModel):
    items: list[WorkflowResponse]
    total: int
    page: int
    limit: int


# ── Workflow Run ─────────────────────────────────────────────────────

class WorkflowRunResponse(BaseModel):
    id: UUID
    workflow_id: UUID
    user_id: UUID
    status: str
    trigger_type: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    node_results: dict[str, Any]
    output_data: dict[str, Any] | None = None
    findings_generated: int
    error: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunList(BaseModel):
    items: list[WorkflowRunResponse]
    total: int
    page: int
    limit: int


# ── Workflow Template ────────────────────────────────────────────────

class WorkflowTemplateResponse(BaseModel):
    id: UUID
    user_id: UUID | None = None
    name: str
    description: str | None = None
    category: str
    tags: list[str]
    nodes_template: list[dict[str, Any]]
    edges_template: list[dict[str, Any]]
    variables_schema: list[dict[str, Any]]
    is_system: bool
    is_public: bool
    install_count: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class WorkflowTemplateCreate(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = None
    category: str = "custom"
    tags: list[str] = Field(default_factory=list)
    nodes_template: list[dict[str, Any]] = Field(default_factory=list)
    edges_template: list[dict[str, Any]] = Field(default_factory=list)
    variables_schema: list[dict[str, Any]] = Field(default_factory=list)


# ── From Template / NL ───────────────────────────────────────────────

class WorkflowFromTemplate(BaseModel):
    template_id: UUID
    project_id: UUID | None = None
    variables: dict[str, Any] = Field(default_factory=dict)
    name: str | None = None


class WorkflowFromDescription(BaseModel):
    description: str
    project_id: UUID | None = None
