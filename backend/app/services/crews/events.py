"""Event emission for real-time crew activity tracking."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ...models.agent_crew import ActivityType, AgentActivity


async def emit_event(
    db: Session,
    mission_id: uuid.UUID,
    activity_type: ActivityType,
    content: str,
    *,
    run_id: uuid.UUID | None = None,
    crew_id: uuid.UUID | None = None,
    expert_agent_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
    confidence: float | None = None,
) -> AgentActivity:
    """Persist an activity event and return it.

    In the future this will also publish to Redis pub/sub for WebSocket delivery.
    """
    activity = AgentActivity(
        id=uuid.uuid4(),
        mission_id=mission_id,
        run_id=run_id,
        crew_id=crew_id,
        expert_agent_id=expert_agent_id,
        activity_type=activity_type,
        content=content,
        metadata_json=metadata or {},
        confidence=confidence,
    )
    db.add(activity)
    db.flush()  # Flush so the activity gets an ID without committing the transaction
    return activity


async def emit_crew_run_started(
    db: Session,
    mission_id: uuid.UUID,
    run_id: uuid.UUID,
    crew_id: uuid.UUID,
    expert_names: list[str],
) -> AgentActivity:
    return await emit_event(
        db,
        mission_id,
        ActivityType.delegating,
        f"Crew run started with experts: {', '.join(expert_names)}",
        run_id=run_id,
        crew_id=crew_id,
        metadata={"event": "CREW_RUN_STARTED", "experts": expert_names},
    )


async def emit_crew_run_completed(
    db: Session,
    mission_id: uuid.UUID,
    run_id: uuid.UUID,
    crew_id: uuid.UUID,
    findings_count: int,
) -> AgentActivity:
    return await emit_event(
        db,
        mission_id,
        ActivityType.writing,
        f"Crew run completed with {findings_count} findings",
        run_id=run_id,
        crew_id=crew_id,
        metadata={"event": "CREW_RUN_COMPLETED", "findings_count": findings_count},
    )


async def emit_expert_thinking(
    db: Session,
    mission_id: uuid.UUID,
    run_id: uuid.UUID,
    crew_id: uuid.UUID,
    expert_agent_id: uuid.UUID,
    expert_name: str,
    expert_icon: str,
    thought: str,
    action: str,
    tool: str | None = None,
    result_preview: str | None = None,
) -> AgentActivity:
    """Emit an EXPERT_THINKING event — the main live dashboard feed item."""
    # Map action to activity type
    type_map = {
        "searching": ActivityType.searching,
        "scraping": ActivityType.scraping,
        "calling": ActivityType.calling,
        "analyzing": ActivityType.analyzing,
        "thinking": ActivityType.thinking,
        "writing": ActivityType.writing,
        "synthesizing": ActivityType.synthesizing,
    }
    activity_type = type_map.get(action, ActivityType.thinking)

    return await emit_event(
        db,
        mission_id,
        activity_type,
        f"{expert_icon} {expert_name}: {thought}",
        run_id=run_id,
        crew_id=crew_id,
        expert_agent_id=expert_agent_id,
        metadata={
            "event": "EXPERT_THINKING",
            "expert_name": expert_name,
            "expert_icon": expert_icon,
            "thought": thought,
            "action": action,
            "tool": tool,
            "result_preview": (result_preview or "")[:200],
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


async def emit_task_started(
    db: Session,
    mission_id: uuid.UUID,
    run_id: uuid.UUID,
    crew_id: uuid.UUID,
    expert_agent_id: uuid.UUID,
    expert_name: str,
    task_type: str,
) -> AgentActivity:
    return await emit_event(
        db,
        mission_id,
        ActivityType.thinking,
        f"{expert_name} started {task_type}",
        run_id=run_id,
        crew_id=crew_id,
        expert_agent_id=expert_agent_id,
        metadata={"event": "CREW_TASK_STARTED", "task_type": task_type},
    )


async def emit_task_completed(
    db: Session,
    mission_id: uuid.UUID,
    run_id: uuid.UUID,
    crew_id: uuid.UUID,
    expert_agent_id: uuid.UUID,
    expert_name: str,
    task_type: str,
    findings_count: int,
) -> AgentActivity:
    return await emit_event(
        db,
        mission_id,
        ActivityType.found_data,
        f"{expert_name} completed {task_type} — {findings_count} findings",
        run_id=run_id,
        crew_id=crew_id,
        expert_agent_id=expert_agent_id,
        metadata={
            "event": "CREW_TASK_COMPLETED",
            "task_type": task_type,
            "findings_count": findings_count,
        },
    )


async def emit_finding_added(
    db: Session,
    mission_id: uuid.UUID,
    run_id: uuid.UUID,
    finding_title: str,
    confidence: float,
    source: str | None,
) -> AgentActivity:
    return await emit_event(
        db,
        mission_id,
        ActivityType.found_insight,
        f"Finding: {finding_title} (confidence: {confidence:.0%})",
        run_id=run_id,
        confidence=confidence,
        metadata={
            "event": "RESEARCH_FINDING_ADDED",
            "finding_title": finding_title,
            "confidence": confidence,
            "source": source,
        },
    )
