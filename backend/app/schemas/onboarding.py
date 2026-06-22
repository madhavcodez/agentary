"""Schemas for project onboarding and question generation endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator

# ── Request schemas ──────────────────────────────────────────────────


class GenerateQuestionsRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    project_type: str = Field(min_length=1, max_length=100)


class ConfigureAndStartRequest(BaseModel):
    answers: dict[str, str | list[str]] = Field(default_factory=dict)
    project_title: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _validate_answers(self) -> ConfigureAndStartRequest:
        if len(self.answers) > 20:
            raise ValueError("Too many answers (max 20)")
        for key, value in self.answers.items():
            # Flatten list answers to comma-separated string for downstream use
            if isinstance(value, list):
                flat = ", ".join(value)
                if len(flat) > 2000:
                    raise ValueError(f"Answer for '{key}' exceeds 2000 characters")
                self.answers[key] = flat
            elif len(value) > 2000:
                raise ValueError(f"Answer for '{key}' exceeds 2000 characters")
        return self


# ── Response schemas ─────────────────────────────────────────────────


class OnboardingQuestion(BaseModel):
    id: str
    question: str
    type: str  # text | select | multiselect
    options: list[str] | None = None
    placeholder: str | None = None


class GenerateQuestionsResponse(BaseModel):
    questions: list[OnboardingQuestion]


class ConfigureAndStartResponse(BaseModel):
    project: dict[str, Any]
    mission: dict[str, Any]


class SynthesizeReportResponse(BaseModel):
    report: dict[str, Any]
