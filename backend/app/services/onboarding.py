"""Service layer for project onboarding (question generation + configure-and-start)."""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..config import settings
from ..models.project import Project
from ..prompts.onboarding import (
    build_questions_prompt,
    QUESTIONS_SCHEMA_HINT,
    get_fallback_questions,
)

logger = logging.getLogger(__name__)


async def _redis_get(key: str) -> dict | None:
    """Non-fatal Redis cache read. Returns None on miss or error."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            raw = await r.get(key)
            return json.loads(raw) if raw else None
        finally:
            await r.aclose()
    except Exception as exc:
        logger.debug("Redis cache read failed (non-fatal): %s", exc)
        return None


async def _redis_set(key: str, value: Any, ttl: int = 3600) -> None:
    """Non-fatal Redis cache write."""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await r.setex(key, ttl, json.dumps(value, default=str))
        finally:
            await r.aclose()
    except Exception as exc:
        logger.debug("Redis cache write failed (non-fatal): %s", exc)


async def generate_onboarding_questions(
    project: Project,
    title: str,
    project_type: str,
) -> dict:
    """Generate AI-powered onboarding questions for a project.

    Uses Redis cache (keyed by project_type, 1h TTL) and falls back to
    hardcoded templates when Gemini is unavailable.
    """
    from ..services.gemini import generate_structured

    # Check cache first
    cache_key = f"onboarding:questions:{project_type}"
    cached = await _redis_get(cache_key)
    if cached is not None:
        logger.info("Cache hit for onboarding questions (type=%s)", project_type)
        return cached

    # Call Gemini
    prompt = build_questions_prompt(title=title, project_type=project_type)
    try:
        result = await generate_structured(prompt, schema_hint=QUESTIONS_SCHEMA_HINT)
    except Exception as exc:
        logger.error("Gemini question generation failed for project %s: %s", project.id, exc)
        fallback = get_fallback_questions(project_type)
        logger.info("Returning fallback questions for project_type=%s", project_type)
        return {"questions": fallback}

    questions_raw = result.get("questions", [])
    if not isinstance(questions_raw, list) or len(questions_raw) == 0:
        fallback = get_fallback_questions(project_type)
        logger.info("Gemini returned empty questions, using fallback for project_type=%s", project_type)
        return {"questions": fallback}

    questions = [
        {
            "id": q.get("id", f"q{i + 1}"),
            "question": q.get("question", ""),
            "type": q.get("type", "text"),
            "options": q.get("options"),
            "placeholder": q.get("placeholder", ""),
        }
        for i, q in enumerate(questions_raw)
    ]

    payload = {"questions": questions}

    # Cache the result
    await _redis_set(cache_key, payload)

    return payload


async def synthesize_domain_context(
    project_title: str,
    answers: dict[str, str],
) -> str:
    """Synthesize a domain context string from onboarding Q&A via Gemini.

    Falls back to raw Q&A text if Gemini fails.
    """
    from ..services.gemini import generate_text
    from ..prompts.onboarding import build_context_prompt, CONTEXT_SYSTEM_INSTRUCTION

    prompt = build_context_prompt(project_title=project_title, answers=answers)
    try:
        return (await generate_text(prompt=prompt, system=CONTEXT_SYSTEM_INSTRUCTION)).strip()
    except Exception as exc:
        logger.error("Failed to synthesize domain context: %s", exc)
        answers_text = "\n".join(f"- {k}: {v}" for k, v in answers.items())
        return f"Project: {project_title}\nOnboarding answers:\n{answers_text}"


def create_mission_for_project(
    project: Project,
    user_id: Any,
    domain_context: str,
    project_title: str,
    db: Session,
) -> Any:
    """Create a draft mission linked to the project and flush to DB.

    Returns the new Mission object.
    """
    from ..models.mission import Mission, MissionStatus

    mission_name = f"Research: {project_title}"
    if len(mission_name) > 255:
        mission_name = mission_name[:252] + "..."

    mission = Mission(
        project_id=project.id,
        user_id=user_id,
        name=mission_name,
        description=f"Auto-generated mission for project '{project_title}'",
        objective=domain_context,
        status=MissionStatus.draft,
        mission_type="research",
    )
    db.add(mission)
    db.flush()
    db.refresh(mission)

    project.domain_context = domain_context
    project.total_missions = (project.total_missions or 0) + 1
    db.flush()

    return mission
