"""Question generator — STORM pre-writing step 2.

One Flash call per perspective returns that perspective's full question set
in a single structured response. The N*M explosion (perspectives * questions)
is deliberately collapsed to N calls via batched output — the model receives
``max_questions`` and returns up to that many in one shot.
"""

from __future__ import annotations

import logging
from typing import Any

from ...prompts.storm import QUESTION_SCHEMA_HINT, build_question_prompt
from .budget import StormBudget

logger = logging.getLogger(__name__)

_VALID_EVIDENCE_TYPES = {
    "fact",
    "trend",
    "comparison",
    "expert_opinion",
    "example",
    "challenge",
}


async def generate_questions(
    *,
    mission: Any,
    perspective: dict[str, Any],
    budget: StormBudget,
    max_questions: int,
) -> list[dict[str, Any]]:
    """Return ``[{text, priority, evidence_type}, ...]`` for one perspective."""
    from ..gemini import generate_structured

    prompt = build_question_prompt(
        mission_name=mission.name,
        objective=getattr(mission, "objective", None),
        perspective=perspective,
        max_questions=max_questions,
    )

    budget.inc("flash")
    try:
        result = await generate_structured(prompt, schema_hint=QUESTION_SCHEMA_HINT)
    except Exception as exc:
        logger.warning(
            "question_generator: call failed for perspective=%s mission=%s: %s",
            perspective.get("role"),
            mission.id,
            exc,
        )
        return []

    raw = result.get("questions")
    if not isinstance(raw, list):
        return []

    out: list[dict[str, Any]] = []
    for item in raw[:max_questions]:
        if not isinstance(item, dict):
            continue
        text = (item.get("text") or "").strip()
        if not text:
            continue
        priority = _coerce_priority(item.get("priority"))
        evidence_type = (item.get("evidence_type") or "fact").strip().lower()
        if evidence_type not in _VALID_EVIDENCE_TYPES:
            evidence_type = "fact"
        out.append(
            {
                "text": text[:500],
                "priority": priority,
                "evidence_type": evidence_type,
            }
        )
    return out


def _coerce_priority(raw: Any) -> float:
    try:
        p = float(raw)
    except (TypeError, ValueError):
        return 0.5
    if p < 0.0:
        return 0.0
    if p > 1.0:
        return 1.0
    return p
