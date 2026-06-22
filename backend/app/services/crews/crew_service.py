"""Crew service — assembles crews, starts runs, provides status."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from ...models.agent_crew import AgentCrew, CoordinationStrategy
from ...models.crew_run import CrewRun
from ...models.crew_task import CrewTask
from ...models.expert_agent import ExpertAgent
from ...models.mission import Mission, MissionStatus
from .expert_registry import select_experts_for_mission
from .task_planner import plan_tasks


async def assemble_crew(
    mission: Mission,
    db: Session,
    expert_slugs: list[str] | None = None,
) -> AgentCrew:
    """Select experts and create an AgentCrew for a mission.

    If expert_slugs is provided, use those specific experts.
    Otherwise, use Gemini to auto-select the best experts.
    """
    if expert_slugs:
        experts = (
            db.query(ExpertAgent)
            .filter(ExpertAgent.slug.in_(expert_slugs), ExpertAgent.is_active.is_(True))
            .all()
        )
    else:
        max_experts = (mission.crew_config or {}).get("max_experts", 5)
        experts = await select_experts_for_mission(
            mission_name=mission.name,
            mission_description=mission.description,
            mission_objective=mission.objective,
            parameters=mission.parameters,
            db=db,
            max_experts=max_experts,
        )

    if not experts:
        raise ValueError("No experts available for this mission")

    # Build agents JSONB
    agents_config = []
    for expert in experts:
        agents_config.append(
            {
                "agent_id": str(expert.id),
                "slug": expert.slug,
                "name": expert.name,
                "role": expert.specialty.value if expert.specialty else "researcher",
                "icon": expert.icon,
            }
        )

    crew = AgentCrew(
        id=uuid.uuid4(),
        mission_id=mission.id,
        agents=agents_config,
        coordination_strategy=CoordinationStrategy.parallel,
    )
    db.add(crew)
    db.commit()
    db.refresh(crew)
    return crew


async def start_crew_run(
    crew: AgentCrew,
    mission: Mission,
    db: Session,
    trigger_type: str = "manual",
) -> CrewRun:
    """Create a CrewRun with planned tasks and return it (ready for execution)."""
    # Load experts
    agent_ids = [a.get("agent_id") for a in (crew.agents or []) if a.get("agent_id")]
    experts = db.query(ExpertAgent).filter(ExpertAgent.id.in_(agent_ids)).all()
    expert_map = {e.slug: e for e in experts}

    # Plan tasks via Gemini
    task_plan = await plan_tasks(mission, experts, db)

    # Create the run
    run = CrewRun(
        id=uuid.uuid4(),
        mission_id=mission.id,
        status="queued",
        trigger_type=trigger_type,
        metrics={},
    )
    db.add(run)
    db.flush()

    # Create crew tasks from plan
    for task_data in task_plan:
        expert = expert_map.get(task_data["expert_slug"])
        if not expert:
            continue

        crew_task = CrewTask(
            id=uuid.uuid4(),
            mission_run_id=run.id,
            expert_agent_id=expert.id,
            task_type=task_data["task_type"],
            description=task_data["description"],
            input_data=task_data.get("input_data", {}),
            status="pending",
        )
        db.add(crew_task)

    # Update mission status
    mission.status = MissionStatus.queued
    db.commit()
    db.refresh(run)
    return run


def get_crew_status(crew_id: uuid.UUID, db: Session) -> dict[str, Any]:
    """Get real-time status for a crew."""
    crew = db.query(AgentCrew).filter_by(id=crew_id).first()
    if not crew:
        raise ValueError(f"Crew {crew_id} not found")

    latest_run = (
        db.query(CrewRun).filter_by(crew_id=crew_id).order_by(CrewRun.created_at.desc()).first()
    )

    tasks_status = []
    if latest_run:
        for task in latest_run.tasks:
            expert = db.query(ExpertAgent).filter_by(id=task.expert_agent_id).first()
            tasks_status.append(
                {
                    "task_id": str(task.id),
                    "expert_name": expert.name if expert else "Unknown",
                    "expert_icon": expert.icon if expert else "\U0001f916",
                    "task_type": task.task_type,
                    "status": task.status,
                    "thinking_log": task.thinking_log or [],
                    "findings_produced": task.findings_produced,
                    "duration_seconds": task.duration_seconds,
                }
            )

    return {
        "crew_id": str(crew.id),
        "coordination_strategy": (
            crew.coordination_strategy.value if crew.coordination_strategy else "parallel"
        ),
        "agents": crew.agents or [],
        "latest_run": (
            {
                "run_id": str(latest_run.id) if latest_run else None,
                "status": latest_run.status if latest_run else None,
                "started_at": (
                    latest_run.started_at.isoformat()
                    if latest_run and latest_run.started_at
                    else None
                ),
                "duration_seconds": latest_run.duration_seconds,
                "metrics": latest_run.metrics,
                "tasks": tasks_status,
            }
            if latest_run
            else None
        ),
    }
