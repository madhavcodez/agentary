from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AlertCreate(BaseModel):
    monitor_id: UUID
    project_id: UUID | None = None
    alert_type: str
    severity: str = "low"
    title: str
    message: str | None = None
    data: dict | None = None
    notification_channels: list | None = None


class AlertUpdate(BaseModel):
    is_read: bool | None = None
    read_at: datetime | None = None
    notification_sent: bool | None = None
    notification_channels: list | None = None


class AlertRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    monitor_id: UUID
    project_id: UUID | None = None
    user_id: UUID
    alert_type: str
    severity: str
    title: str
    message: str | None = None
    data: dict | None = None
    is_read: bool
    read_at: datetime | None = None
    notification_sent: bool
    notification_channels: list | None = None
    created_at: datetime
    updated_at: datetime
