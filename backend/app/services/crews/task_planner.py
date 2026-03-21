"""Task planner — uses Gemini to analyze a mission and create a task plan."""
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
        expert_info.append({
            "slug": e.slug,
            "name": e.name,
            "specialty": e.specialty.value if e.specialty else "unknown",
            "tools": tools,
            "description": e.description,
        })

    prompt = (
        "You are a research mission planner. Given a mission and available experts, "
        "create a detailed task plan.\n\n"
        f"## Mission\n"
        f"Name: {mission.name}\n"
        f"Description: {mission.description or 'N/A'}\n"
        f"Objective: {mission.objective or 'N/A'}\n"
        f"Parameters: {json.dumps(mission.parameters or {})}\n\n"
        f"## Available Experts\n"
        f"{json.dumps(expert_info, indent=2)}\n\n"
        "## Instructions\n"
        "Create a task plan as a JSON array. Each task should have:\n"
        "- `expert_slug`: which expert handles this task\n"
        "- `task_type`: one of web_search, api_query, voice_call, data_analysis, "
        "synthesis, report_writing, entity_extraction, comparison, trend_analysis, "
        "fact_verification\n"
        "- `description`: specific instructions for the expert\n"
        "- `input_data`: relevant context/queries as a JSON object\n"
        "- `priority`: 1 (highest) to 5 (lowest)\n"
        "- `phase`: 'research', 'synthesis', or 'report'\n\n"
        "Rules:\n"
        "- Research tasks (phase='research') run in parallel\n"
        "- Synthesis tasks (phase='synthesis') run after all research completes\n"
        "- Report tasks (phase='report') run last\n"
        "- Each research expert should have 1-3 specific tasks\n"
        "- Synthesizer always gets a synthesis task\n"
        "- Report writer always gets a report_writing task\n"
        "- Be specific in descriptions — tell experts exactly what to search/analyze\n\n"
        "Return JSON: {\"tasks\": [...]}"
    )

    result = await generate_structured(prompt)
    tasks = result.get("tasks", [])

    # Validate and normalize
    valid_types = {
        "web_search", "api_query", "voice_call", "data_analysis",
        "synthesis", "report_writing", "entity_extraction",
        "comparison", "trend_analysis", "fact_verification",
    }
    valid_phases = {"research", "synthesis", "report"}
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

        validated.append({
            "expert_slug": slug,
            "task_type": task_type,
            "description": task.get("description", "Research the mission topic"),
            "input_data": task.get("input_data", {}),
            "priority": min(max(int(task.get("priority", 3)), 1), 5),
            "phase": phase,
        })

    # Ensure synthesizer and report-writer have tasks
    has_synthesis = any(t["phase"] == "synthesis" for t in validated)
    has_report = any(t["phase"] == "report" for t in validated)

    if not has_synthesis and "synthesizer" in expert_slugs:
        validated.append({
            "expert_slug": "synthesizer",
            "task_type": "synthesis",
            "description": "Combine all research findings, resolve contradictions, identify gaps, and provide overall assessment.",
            "input_data": {},
            "priority": 1,
            "phase": "synthesis",
        })

    if not has_report and "report-writer" in expert_slugs:
        validated.append({
            "expert_slug": "report-writer",
            "task_type": "report_writing",
            "description": "Generate a polished research report with executive summary, sections, charts, and citations.",
            "input_data": {},
            "priority": 1,
            "phase": "report",
        })

    return validated
