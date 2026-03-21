from __future__ import annotations

import enum
import json
import logging
from datetime import datetime
from typing import Any, Callable
from uuid import UUID

logger = logging.getLogger(__name__)


class EventType(str, enum.Enum):
    # Project events
    project_created = "project.created"
    project_updated = "project.updated"
    project_archived = "project.archived"

    # Mission events
    mission_created = "mission.created"
    mission_started = "mission.started"
    mission_completed = "mission.completed"
    mission_failed = "mission.failed"
    mission_paused = "mission.paused"

    # Agent activity events
    agent_thinking = "agent.thinking"
    agent_searching = "agent.searching"
    agent_scraping = "agent.scraping"
    agent_calling = "agent.calling"
    agent_analyzing = "agent.analyzing"
    agent_writing = "agent.writing"
    agent_found_data = "agent.found_data"
    agent_found_insight = "agent.found_insight"
    agent_error = "agent.error"

    # Finding events
    finding_created = "finding.created"
    finding_verified = "finding.verified"
    finding_contradicted = "finding.contradicted"

    # Call events
    call_started = "call.started"
    call_connected = "call.connected"
    call_completed = "call.completed"
    call_failed = "call.failed"

    # Monitor events
    monitor_triggered = "monitor.triggered"
    monitor_alert = "monitor.alert"

    # Report events
    report_generating = "report.generating"
    report_completed = "report.completed"
    report_failed = "report.failed"


class Event:
    def __init__(
        self,
        event_type: EventType,
        data: dict[str, Any],
        project_id: UUID | str | None = None,
        mission_id: UUID | str | None = None,
        user_id: UUID | str | None = None,
    ):
        self.event_type = event_type
        self.data = data
        self.project_id = str(project_id) if project_id else None
        self.mission_id = str(mission_id) if mission_id else None
        self.user_id = str(user_id) if user_id else None
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "project_id": self.project_id,
            "mission_id": self.mission_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)


class EventBus:
    """Simple in-process event bus. Redis pub/sub integration added in later phases."""

    def __init__(self):
        self._subscribers: dict[EventType, list[Callable]] = {}

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Event) -> None:
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                result = handler(event)
                if hasattr(result, "__await__"):
                    await result
            except Exception:
                logger.exception("Error in event handler for %s", event.event_type)

    async def broadcast(self, event: Event) -> None:
        """Broadcast to in-process subscribers AND to Redis for WebSocket relay."""
        await self.publish(event)
        try:
            from .redis_bridge import publish_event
            await publish_event(event)
        except Exception:
            logger.debug("Redis publish skipped (not available)")
        logger.info("Event broadcast: %s", event.event_type.value)


# Global event bus instance
event_bus = EventBus()
