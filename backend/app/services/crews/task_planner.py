"""Task planner — uses Gemini to analyze a mission and create a task plan.

Uses DeerFlow's 4-phase deep-research methodology:
  Phase 1 (scout):     Broad exploration to identify research dimensions
  Phase 2 (research):  Parallel deep dives per dimension with multi-angle coverage
  Phase 3 (gap_check): Audit completeness across 6 info categories
  Phase 4 (synthesis + report): Synthesize findings and generate report
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from ...models.expert_agent import ExpertAgent
from ...models.mission import Mission
from ..gemini import generate_structured


async def plan_tasks(
    mission: Mission,
    experts: list[ExpertAgent],
    db: Session,
) -> list[dict[str, Any]]:
    """Use Gemini to analyze a mission and create a task plan for the crew.

    Returns a list of task dicts:
    [
        {
            "expert_slug": "web-researcher",
            "task_type": "web_search",
            "description": "Search for ...",
            "input_data": {"query": "..."},
            "priority": 1,
        },
        ...
    ]
    """
    expert_info = []
    for e in experts:
        tools = e.tools if isinstance(e.tools, list) else []
        expert_info.append(
            {
                "slug": e.slug,
                "name": e.name,
                "specialty": e.specialty.value if e.specialty else "unknown",
                "tools": tools,
                "description": e.description,
            }
        )

    prompt = (
        "You are a research mission planner using the DeerFlow deep-research methodology.\n\n"
        f"## Mission\n"
        f"Name: {mission.name}\n"
        f"Description: {mission.description or 'N/A'}\n"
        f"Objective: {mission.objective or 'N/A'}\n"
        f"Parameters: {json.dumps(mission.parameters or {})}\n\n"
        f"## Available Experts\n"
        f"{json.dumps(expert_info, indent=2)}\n\n"
        "## DeerFlow Research Methodology\n"
        "Plan research in 4 phases for maximum depth and coverage:\n\n"
        "**Phase 1 — Scout (phase='scout'):** A single broad exploration task to map\n"
        "the research landscape. Identify key dimensions, stakeholders, data sources,\n"
        "and angles that need deeper investigation. Assign to the most versatile\n"
        "research expert.\n\n"
        "**Phase 2 — Research (phase='research'):** Parallel deep-dive tasks, one per\n"
        "identified dimension. Each task should target MULTIPLE angles:\n"
        "  - Facts & data (statistics, numbers, market data)\n"
        "  - Examples & cases (real-world implementations)\n"
        "  - Expert opinions (analyst/authority perspectives)\n"
        "  - Trends & predictions (forward-looking analysis)\n"
        "  - Comparisons (alternatives, competitive context)\n"
        "  - Challenges & criticisms (balanced critical view)\n\n"
        "**Phase 3 — Gap Check (phase='gap_check'):** After all research completes,\n"
        "a synthesizer audits findings for completeness. If gaps exist, specify what's\n"
        "missing. This task receives all findings as input.\n\n"
        "**Phase 4 — Synthesis + Report (phase='synthesis' then 'report'):**\n"
        "Synthesizer resolves contradictions and produces assessment. Report writer\n"
        "generates the final structured output.\n\n"
        "## Task Schema\n"
        "Each task must have:\n"
        "- `expert_slug`: which expert handles this task\n"
        "- `task_type`: one of web_search, api_query, voice_call, data_analysis, "
        "synthesis, report_writing, entity_extraction, comparison, trend_analysis, "
        "fact_verification, scout, gap_check\n"
        "- `description`: specific instructions for the expert\n"
        "- `input_data`: relevant context/queries as a JSON object\n"
        "- `priority`: 1 (highest) to 5 (lowest)\n"
        "- `phase`: 'scout', 'research', 'gap_check', 'synthesis', or 'report'\n\n"
        "Rules:\n"
        "- Scout task runs first (exactly 1 task, phase='scout')\n"
        "- Research tasks (phase='research') run in parallel after scout\n"
        "- Gap check (phase='gap_check') runs after all research completes\n"
        "- Synthesis tasks (phase='synthesis') run after gap check\n"
        "- Report tasks (phase='report') run last\n"
        "- Each research expert should have 1-3 specific deep-dive tasks\n"
        "- Be specific in descriptions — tell experts exactly what to search/analyze\n"
        "- Research tasks should cover different DIMENSIONS, not repeat the same angle\n\n"
        'Return JSON: {"tasks": [...]}'
    )

    result = await generate_structured(prompt)
    tasks = result.get("tasks", [])

    # Validate and normalize
    valid_types = {
        "web_search",
        "api_query",
        "voice_call",
        "data_analysis",
        "synthesis",
        "report_writing",
        "entity_extraction",
        "comparison",
        "trend_analysis",
        "fact_verification",
        "scout",
        "gap_check",
    }
    valid_phases = {"scout", "research", "gap_check", "synthesis", "report"}
    expert_slugs = {e.slug for e in experts}

    validated = []
    for task in tasks:
        if not isinstance(task, dict):
            continue
        slug = task.get("expert_slug", "")
        if slug not in expert_slugs:
            continue
        task_type = task.get("task_type", "web_search")
        if task_type not in valid_types:
            task_type = "web_search"
        phase = task.get("phase", "research")
        if phase not in valid_phases:
            phase = "research"

        validated.append(
            {
                "expert_slug": slug,
                "task_type": task_type,
                "description": task.get("description", "Research the mission topic"),
                "input_data": task.get("input_data", {}),
                "priority": min(max(int(task.get("priority", 3)), 1), 5),
                "phase": phase,
            }
        )

    # Ensure all DeerFlow phases have at least one task
    has_scout = any(t["phase"] == "scout" for t in validated)
    has_gap_check = any(t["phase"] == "gap_check" for t in validated)
    has_synthesis = any(t["phase"] == "synthesis" for t in validated)
    has_report = any(t["phase"] == "report" for t in validated)

    # Scout: pick the first research-capable expert
    if not has_scout:
        scout_slug = next(
            (
                s
                for s in ("web-researcher", "competitive-intel", "market-analyst")
                if s in expert_slugs
            ),
            next(iter(expert_slugs), None),
        )
        if scout_slug:
            validated.insert(
                0,
                {
                    "expert_slug": scout_slug,
                    "task_type": "scout",
                    "description": (
                        "Broad exploration: survey the research landscape for this mission. "
                        "Identify key dimensions, stakeholders, data sources, and angles "
                        "that need deeper investigation. Return structured dimensions."
                    ),
                    "input_data": {},
                    "priority": 1,
                    "phase": "scout",
                },
            )

    # Gap check: assign to synthesizer or first available
    if not has_gap_check and "synthesizer" in expert_slugs:
        validated.append(
            {
                "expert_slug": "synthesizer",
                "task_type": "gap_check",
                "description": (
                    "Audit research completeness using DeerFlow diversity criteria: "
                    "Facts & Data, Examples & Cases, Expert Opinions, Trends & Predictions, "
                    "Comparisons, Challenges & Criticisms. Identify missing angles and "
                    "recommend additional research if gaps exist."
                ),
                "input_data": {},
                "priority": 1,
                "phase": "gap_check",
            }
        )

    if not has_synthesis and "synthesizer" in expert_slugs:
        validated.append(
            {
                "expert_slug": "synthesizer",
                "task_type": "synthesis",
                "description": "Combine all research findings, resolve contradictions, identify gaps, and provide overall assessment.",
                "input_data": {},
                "priority": 1,
                "phase": "synthesis",
            }
        )

    if not has_report and "report-writer" in expert_slugs:
        validated.append(
            {
                "expert_slug": "report-writer",
                "task_type": "report_writing",
                "description": "Generate a polished research report with executive summary, sections, charts, and citations.",
                "input_data": {},
                "priority": 1,
                "phase": "report",
            }
        )

    return validated
