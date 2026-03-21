from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DataSourceCreate(BaseModel):
    name: str
    slug: str
    source_type: str = "api"
    provider: str
    description: str | None = None
    config: dict[str, Any] = {}
    auth_config: dict[str, Any] = {}
    rate_limit: dict[str, Any] = {}
    cost_per_request: float | None = None


class DataSourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    auth_config: dict[str, Any] | None = None
    rate_limit: dict[str, Any] | None = None
    cost_per_request: float | None = None
    is_active: bool | None = None


class DataSourceResponse(BaseModel):
    id: UUID
    user_id: UUID | None = None
    name: str
    slug: str
    source_type: str
    provider: str
    description: str | None = None
    config: dict[str, Any] = {}
    rate_limit: dict[str, Any] = {}
    cost_per_request: float | None = None
    is_system: bool
    is_active: bool
    health_status: str
    last_health_check: datetime | None = None
    total_requests: int
    total_cost_usd: float
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class DataSourceHealthResponse(BaseModel):
    status: str
    latency_ms: int | None = None
    message: str | None = None


class DataSourceQueryRequest(BaseModel):
    method: str = "search"
    query: str | None = None
    identifier: str | None = None
    params: dict[str, Any] = {}


class DataSourceQueryResponse(BaseModel):
    data: list[dict[str, Any]]
    total_results: int
    source_name: str
    cost_usd: float
    cached: bool
    metadata: dict[str, Any] = {}
