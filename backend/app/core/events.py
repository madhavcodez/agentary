"""Typed event system for cross-service real-time communication."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EventType(str, Enum):
    # Scout / ingest activity
    SCOUT_PHASE_START = "scout.phase.start"
    SCOUT_PHASE_DONE = "scout.phase.done"
    SCOUT_SOURCE_UPDATE = "scout.source.update"
    SCOUT_JOB_SCORED = "scout.job.scored"
    SCOUT_COMPLETE = "scout.complete"

    # Autopilot / workflow
    WORKFLOW_START = "workflow.start"
    WORKFLOW_STEP = "workflow.step"
    WORKFLOW_COMPLETE = "workflow.complete"

    # Monitor / alerts
    MONITOR_CHECK_START = "monitor.check.start"
    MONITOR_CHECK_DONE = "monitor.check.done"
    MONITOR_CHANGE_DETECTED = "monitor.change.detected"
    ALERT_CREATED = "alert.created"

    # System
    SYSTEM_STATUS = "system.status"
    SYSTEM_ERROR = "system.error"


class EventScope(str, Enum):
    GLOBAL = "global"
    USER = "user"
    PROJECT = "project"


@dataclass(frozen=True)
class Event:
    event_type: EventType
    scope: EventScope
    data: dict[str, Any]
    user_id: str | None = None
    project_id: str | None = None
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        d["scope"] = self.scope.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Event:
        return cls(
            event_type=EventType(d["event_type"]),
            scope=EventScope(d["scope"]),
            data=d["data"],
            user_id=d.get("user_id"),
            project_id=d.get("project_id"),
            event_id=d.get("event_id", str(uuid.uuid4())),
            timestamp=d.get("timestamp", time.time()),
        )


# ── In-process event bus (for single-process convenience) ──────────

_listeners: list = []


def on_event(callback):
    """Register a synchronous listener for all events."""
    _listeners.append(callback)
    return callback


async def emit_event(event: Event) -> None:
    """Emit event to in-process listeners AND to Redis pub/sub."""
    for listener in _listeners:
        try:
            listener(event)
        except Exception:
            pass

    # Publish to Redis for cross-process delivery
    from .redis_bridge import publish_event

    await publish_event(event)
