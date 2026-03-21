from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SkillSchema(BaseModel):
    id: UUID | None = None
    name: str
    category: str | None = None
    years_experience: str | None = None
    proficiency: str | None = None

    model_config = {"from_attributes": True}


class ExperienceSchema(BaseModel):
    id: UUID | None = None
    company: str
    title: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    evidence: str | None = None

    model_config = {"from_attributes": True}


class PreferenceSchema(BaseModel):
    id: UUID | None = None
    key: str
    value: str

    model_config = {"from_attributes": True}


class ProfileResponse(BaseModel):
    id: UUID
    name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[SkillSchema] = []
    experiences: list[ExperienceSchema] = []
    preferences: list[PreferenceSchema] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    summary: str | None = None
    skills: list[SkillSchema] | None = None
    experiences: list[ExperienceSchema] | None = None
    preferences: list[PreferenceSchema] | None = None


class ResumeUpload(BaseModel):
    resume_text: str
