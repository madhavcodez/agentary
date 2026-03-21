"""Live feed WebSocket endpoint and REST fallbacks."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..auth import verify_token
from ..core.events import Event, EventScope, EventType
from ..core.websocket_manager import ws_manager
from ..deps import get_current_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["live-feed"])

# ── In-memory recent events buffer (last 200) ──────────────────────

_recent_events: list[dict] = []
_MAX_RECENT = 200


def _buffer_event(event: Event) -> None:
    """Store event in recent buffer for REST polling fallback."""
    _recent_events.append(event.to_dict())
    if len(_recent_events) > _MAX_RECENT:
        del _recent_events[: len(_recent_events) - _MAX_RECENT]


# Register as in-process listener
from ..core.events import on_event as _register

_register(_buffer_event)


# ── WebSocket endpoint ──────────────────────────────────────────────

@router.websocket("/ws/live-feed")
async def live_feed(websocket: WebSocket, token: str = Query(...)):
    """Real-time event stream. Authenticate via ?token=<jwt>.

    After connection, client can send:
        {"type": "subscribe", "project_id": "..."}
    to scope events to a specific project.
    """
    # Authenticate
    try:
        user_id = verify_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    client = await ws_manager.connect(websocket, str(user_id))

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
        if e.get("scope") == "global"
        or e.get("user_id") == user_id
    ]
    return visible[-limit:]


@router.get("/api/live-feed/active")
async def get_active_info(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return summary of active missions/workflows for the dashboard."""
    from ..models.mission import Mission
    from ..models.crew_run import CrewRun

    user_id = user.id

    # Active missions
    active_missions = (
        db.query(Mission)
        .filter(Mission.user_id == user_id, Mission.status == "active")
        .all()
    )

    # Active crew runs
    active_runs = (
        db.query(CrewRun)
        .filter(CrewRun.status.in_(["running", "pending"]))
        .all()
    )

    return {
        "active_missions": [
            {
                "id": str(m.id),
                "title": m.title,
                "status": m.status,
                "project_id": str(m.project_id) if m.project_id else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in active_missions
        ],
        "active_runs": [
            {
                "id": str(r.id),
                "crew_id": str(r.crew_id),
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
            }
            for r in active_runs
        ],
        "connected_clients": ws_manager.connection_count,
    }
