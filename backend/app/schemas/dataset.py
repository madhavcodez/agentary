from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DataSetCreate(BaseModel):
    project_id: UUID
    mission_id: UUID | None = None
    name: str
    description: str | None = None
    schema_definition: dict | None = None


class DataSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    project_id: UUID
    mission_id: UUID | None = None
    name: str
    description: str | None = None
    schema_definition: dict | None = None
    row_count: int
    created_at: datetime
    updated_at: datetime


class DataRowCreate(BaseModel):
    dataset_id: UUID
    data: dict
    source_finding_id: UUID | None = None


class DataRowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    dataset_id: UUID
    data: dict
    source_finding_id: UUID | None = None
    created_at: datetime
