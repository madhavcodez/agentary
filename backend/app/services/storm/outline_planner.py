"""Outline planner — STORM pre-writing step 3.

Consumes the perspective x question matrix and produces the report
outline BEFORE any retrieval happens. This is STORM's load-bearing
contribution: pre-writing quality correlates with final-report quality
because the outline fixes what evidence the synthesizer is looking for.

The output is a list of sections with ``scope`` (what this section must
answer), ``source_question_ids`` (which questions feed it), and
``expected_evidence_types`` (used by the refinement loop to judge quality).
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from ...prompts.storm import OUTLINE_SCHEMA_HINT, build_outline_prompt
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


async def plan_outline(
    *,
    mission: Any,
    perspectives: Sequence[dict[str, Any]],
    question_matrix: Sequence[dict[str, Any]],
    budget: StormBudget,
    max_sections: int,
) -> dict[str, Any] | None:
    """Return ``{title, sections: [...]}`` or ``None`` on failure."""
    from ..gemini import generate_structured

    if not perspectives or not question_matrix:
        return None

    prompt = build_outline_prompt(
        mission_name=mission.name,
        objective=getattr(mission, "objective", None),
        perspectives=perspectives,
        question_matrix=question_matrix,
        max_sections=max_sections,
    )

    budget.inc("flash")
    try:
        result = await generate_structured(prompt, schema_hint=OUTLINE_SCHEMA_HINT)
    except Exception as exc:
        logger.warning("outline_planner: call failed for mission %s: %s", mission.id, exc)
        return None

    valid_qids = {q["id"] for q in question_matrix}
    sections = _normalise_sections(
        result.get("sections"),
        limit=max_sections,
        valid_question_ids=valid_qids,
    )
    if not sections:
        return None

    title = (result.get("title") or mission.name or "Research Report").strip()[:300]
    return {"title": title, "sections": sections}


def _normalise_sections(
    raw: Any,
    *,
    limit: int,
    valid_question_ids: set[int],
) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for idx, item in enumerate(raw[:limit]):
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        scope = (item.get("scope") or "").strip()
        if not title or not scope:
            continue

        raw_qids = item.get("source_question_ids") or []
        qids: list[int] = []
        if isinstance(raw_qids, list):
            for q in raw_qids[:3]:  # hard cap 3 per section per plan
                try:
                    qid = int(q)
                except (TypeError, ValueError):
                    continue
                if qid in valid_question_ids:
                    qids.append(qid)

        raw_types = item.get("expected_evidence_types") or []
        types_: list[str] = []
        if isinstance(raw_types, list):
            for t in raw_types:
                t_str = str(t).strip().lower()
                if t_str in _VALID_EVIDENCE_TYPES:
                    types_.append(t_str)

        out.append({
            "index": idx,
            "title": title[:300],
            "scope": scope[:800],
            "source_question_ids": qids,
            "expected_evidence_types": types_ or ["fact"],
        })
    return out
