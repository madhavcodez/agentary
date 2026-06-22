"""Live feed WebSocket endpoint and REST fallbacks."""

from __future__ import annotations

import contextlib
import json
import logging
import types
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..auth import verify_token
from ..core.events import Event, event_bus
from ..core.websocket_manager import ws_manager
from ..deps import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live-feed"])

# ── In-memory recent events buffer (last 200) ──────────────────────

_recent_events: list[dict] = []
_MAX_RECENT = 200


def _buffer_event(event: Event) -> None:
    _recent_events.append(event.to_dict())
    if len(_recent_events) > _MAX_RECENT:
        del _recent_events[: len(_recent_events) - _MAX_RECENT]


# Register buffer for all event types
for _et in Event.__class__.__mro__:
    pass
# Subscribe to all events by registering a catch-all via broadcast hook
_original_broadcast = event_bus.broadcast.__func__


async def _broadcast_with_buffer(self, event: Event) -> None:
    _buffer_event(event)
    await _original_broadcast(self, event)


event_bus.broadcast = types.MethodType(_broadcast_with_buffer, event_bus)


# ── WebSocket endpoint ──────────────────────────────────────────────

@router.websocket("/ws/live-feed")
async def live_feed_ws(websocket: WebSocket, token: str = Query(default="")):
    """Real-time event stream. Authenticate via ?token=<jwt>.

    Client can send:
        {"type": "subscribe", "project_id": "..."}
    to scope events to a specific project.
    """
    from ..config import settings
    user_id = None

    if token:
        with contextlib.suppress(Exception):
            user_id = verify_token(token)

    # Dev mode: allow connection without valid token
    if user_id is None:
        if settings.app_env == "dev":
            from ..database import get_session
            from ..deps import _get_or_create_dev_user
            db = next(get_session())
            try:
                dev_user = _get_or_create_dev_user(db)
                user_id = dev_user.id
            finally:
                db.close()
        else:
            await websocket.close(code=4001, reason="Invalid token")
            return

    await ws_manager.connect(websocket, str(user_id))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            if msg_type == "subscribe" and msg.get("project_id"):
                await ws_manager.subscribe_project(
                    websocket, str(user_id), msg["project_id"]
                )
                await websocket.send_json(
                    {"type": "subscribed", "project_id": msg["project_id"]}
                )
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS error for user %s: %s", user_id, exc)
    finally:
        await ws_manager.disconnect(websocket, str(user_id))


# ── Also keep the project-scoped stub for backward compat ──────────

@router.websocket("/api/live-feed/{project_id}")
async def live_feed_project(websocket: WebSocket, project_id: UUID):
    """Project-scoped WebSocket (no auth required — for internal use)."""
    await ws_manager.connect(websocket, "system", str(project_id))
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(websocket, "system")


# ── REST fallbacks ──────────────────────────────────────────────────

@router.get("/api/live-feed/recent")
async def get_recent_events(
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
):
    """Polling fallback: return recent events visible to this user."""
    user_id = str(user.id)
    visible = [
        e for e in _recent_events
        if not e.get("user_id") or e.get("user_id") == user_id
    ]
    return visible[-limit:]


@router.get("/api/live-feed/active")
async def get_active_info(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return summary of active missions/workflows for the dashboard."""
    from ..models.mission import Mission

    user_id = user.id

    active_missions = (
        db.query(Mission)
        .filter(
            Mission.user_id == user_id,
            Mission.status.in_(["queued", "running"]),
        )
        .all()
    )

    return {
        "active_missions": [
            {
                "id": str(m.id),
                "title": m.name,
                "status": m.status.value if hasattr(m.status, "value") else str(m.status),
                "project_id": str(m.project_id) if m.project_id else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in active_missions
        ],
        "active_runs": [],
        "connected_clients": ws_manager.connection_count,
    }
