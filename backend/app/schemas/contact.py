from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContactCreate(BaseModel):
    company: str
    name: str | None = None
    title: str | None = None
    phone: str
    email: str | None = None
    source: str | None = "manual"
    opportunity_id: str | None = None
    notes: str | None = None


class ContactUpdate(BaseModel):
    company: str | None = None
    name: str | None = None
    title: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    notes: str | None = None


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    company: str
    name: str | None = None
    title: str | None = None
    phone: str
    email: str | None = None
    source: str
    opportunity_id: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ContactList(BaseModel):
    items: list[ContactResponse]
    total: int
    page: int
    limit: int
