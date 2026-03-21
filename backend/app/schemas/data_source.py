from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DataSourceCreate(BaseModel):
    name: str
    slug: str
    source_type: str = "api"
    provider: str
    description: str | None = None
    config: dict[str, Any] | None = None
    auth_config: dict[str, Any] | None = None
    rate_limit: dict[str, Any] | None = None
    cost_per_request: float | None = None
    is_active: bool = True


class DataSourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None
    auth_config: dict[str, Any] | None = None
    rate_limit: dict[str, Any] | None = None
    cost_per_request: float | None = None
    is_active: bool | None = None


class DataSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | None = None
    user_id: UUID | None = None
    name: str
    slug: str
    source_type: str
    provider: str
    description: str | None = None
    config: dict[str, Any] | None = None
    rate_limit: dict[str, Any] | None = None
    cost_per_request: float | None = None
    is_system: bool
    is_active: bool
    health_status: str | None = None
    last_health_check: datetime | None = None
    total_requests: int | None = None
    total_cost_usd: float | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DataSourceHealthResponse(BaseModel):
    status: str
    message: str | None = None
    latency_ms: float | None = None
    last_check: datetime | None = None


class DataSourceQueryRequest(BaseModel):
    method: str = "search"
    query: str | None = None
    identifier: str | None = None
    params: dict[str, Any] = {}


class DataSourceQueryResponse(BaseModel):
    data: list[dict[str, Any]] | dict[str, Any] | None = None
    total_results: int | None = None
    source_name: str | None = None
    cost_usd: float | None = None
    cached: bool = False
    metadata: dict[str, Any] | None = None
