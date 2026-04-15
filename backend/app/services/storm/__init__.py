"""Stanford STORM research methodology integration for Agentary.

STORM (Shao et al., NAACL 2024 — stanford-oval/storm) is a pre-writing-first
research methodology: mine perspectives, generate questions, plan an outline,
then synthesize sections with bound evidence. This package implements the
pre-writing stage and the section-level synthesis stage; integration with the
existing DeerFlow-style crew runner lives in
``app.services.crews.crew_runner``.

The public entry point is :func:`run_storm_prewrite` which takes a Mission
and returns a persisted :class:`ResearchOutline` (or ``None`` if the per-mission
Gemini budget was exhausted before completion — caller falls back to the
legacy single-pass synthesis path).
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def should_run_storm(mission: Any) -> bool:
    """Decide whether STORM pre-writing should run for this mission.

    Per-mission ``storm_enabled`` overrides the global flag when set;
    otherwise falls back to ``settings.agentary_storm_enabled``.
    """
    from ...config import settings

    per_mission = getattr(mission, "storm_enabled", None)
    if per_mission is not None:
        return bool(per_mission)
    return bool(getattr(settings, "agentary_storm_enabled", False))


async def run_storm_prewrite(mission: Any, db: Session) -> Any | None:
    """Run STORM pre-writing (perspectives → questions → outline) for a mission.

    Returns the persisted ``ResearchOutline`` row, or ``None`` if the run
    hit ``StormBudgetExceeded`` or any phase returned an empty result. The
    crew runner treats ``None`` as "fall back to legacy synthesis".
    """
    # Imports are local to avoid circulars during app startup and keep the
    # module importable even when optional deps (redis) are missing at
    # collection time.
    from ...config import settings
    from ...models.research_outline import ResearchOutline
    from .budget import StormBudget, StormBudgetExceeded
    from .outline_planner import plan_outline
    from .perspective_miner import mine_perspectives
    from .question_generator import generate_questions

    max_perspectives = int(getattr(settings, "storm_max_perspectives", 4))
    max_questions = int(getattr(settings, "storm_max_questions", 3))
    max_sections = int(getattr(settings, "storm_max_sections", 6))

    budget = StormBudget(mission_id=str(mission.id))

    try:
        perspectives = await mine_perspectives(
            mission=mission,
            budget=budget,
            max_perspectives=max_perspectives,
        )
        if not perspectives:
            logger.warning(
                "STORM pre-write: perspective miner returned 0 perspectives for mission %s",
                mission.id,
            )
            return None

        question_matrix: list[dict[str, Any]] = []
        next_qid = 0
        for p_idx, perspective in enumerate(perspectives):
            questions = await generate_questions(
                mission=mission,
                perspective=perspective,
                budget=budget,
                max_questions=max_questions,
            )
            for q in questions:
                question_matrix.append({
                    "id": next_qid,
                    "perspective_index": p_idx,
                    "text": q["text"],
                    "priority": q.get("priority", 0.5),
                    "evidence_type": q.get("evidence_type", "fact"),
                })
                next_qid += 1

        if not question_matrix:
            logger.warning(
                "STORM pre-write: question matrix empty for mission %s",
                mission.id,
            )
            return None

        outline_plan = await plan_outline(
            mission=mission,
            perspectives=perspectives,
            question_matrix=question_matrix,
            budget=budget,
            max_sections=max_sections,
        )
        if not outline_plan or not outline_plan.get("sections"):
            logger.warning(
                "STORM pre-write: outline planner returned no sections for mission %s",
                mission.id,
            )
            return None

    except StormBudgetExceeded as exc:
        logger.warning(
            "STORM pre-write: budget exhausted for mission %s: %s",
            mission.id,
            exc,
        )
        return None

    outline = ResearchOutline(
        mission_id=mission.id,
        perspectives=perspectives,
        question_matrix=question_matrix,
        sections=outline_plan["sections"],
        title=outline_plan.get("title", mission.name),
        version=1,
        meta={
            "budget_flash_calls": budget.flash_calls,
            "budget_pro_calls": budget.pro_calls,
        },
    )
    db.add(outline)
    db.commit()
    db.refresh(outline)

    logger.info(
        "STORM pre-write complete for mission %s: %d perspectives, %d questions, %d sections (%d Flash calls)",
        mission.id,
        len(perspectives),
        len(question_matrix),
        len(outline.sections),
        budget.flash_calls,
    )
    return outline
