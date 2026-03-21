from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MonitorCreate(BaseModel):
    project_id: UUID
    name: str
    description: str | None = None
    monitor_type: str
    target: dict | None = None
    check_schedule: str | None = None
    alert_rules: list | None = None


class MonitorUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    target: dict | None = None
    check_schedule: str | None = None
    alert_rules: list | None = None


class MonitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    user_id: UUID
    name: str
    description: str | None = None
    status: str
    monitor_type: str
    target: dict | None = None
    check_schedule: str | None = None
    alert_rules: list | None = None
    last_checked_at: datetime | None = None
    last_alert_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    monitor_id: UUID
    project_id: UUID
    severity: str
    title: str
    content: str | None = None
    data: dict | None = None
    acknowledged: bool
    acknowledged_at: datetime | None = None
    created_at: datetime
