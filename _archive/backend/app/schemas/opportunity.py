from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, field_validator
from bs4 import BeautifulSoup


def _strip_html(html: str | None) -> str | None:
    if not html:
        return html
    if "<" in html and ">" in html:
        return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)
    return html


class OpportunityResponse(BaseModel):
    id: UUID
    source: str
    source_id: str
    company: str
    title: str
    location: str | None = None
    description: str | None = None
    url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, v):
        return _strip_html(v)


class OpportunityList(BaseModel):
    items: list[OpportunityResponse]
    total: int
    page: int
    limit: int
