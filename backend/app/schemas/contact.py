from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ContactCreate(BaseModel):
    company: str = Field(..., max_length=255)
    name: str | None = None
    title: str | None = None
    phone: str = Field(..., max_length=50, description="E.164 format phone number")
    email: str | None = None
    source: str = "manual"
    opportunity_id: UUID | None = None
    notes: str | None = None


class ContactUpdate(BaseModel):
    company: str | None = None
    name: str | None = None
    title: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    opportunity_id: UUID | None = None
    notes: str | None = None


class ContactResponse(BaseModel):
    id: UUID
    company: str
    name: str | None = None
    title: str | None = None
    phone: str
    email: str | None = None
    source: str
    opportunity_id: UUID | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ContactList(BaseModel):
    items: list[ContactResponse]
    total: int
    page: int
    limit: int
