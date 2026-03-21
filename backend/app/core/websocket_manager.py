"""WebSocket connection manager with project/user-scoped routing."""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

from .events import Event, EventScope

logger = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    websocket: WebSocket
    user_id: str
    subscribed_projects: set[str] = field(default_factory=set)


class WebSocketManager:
    def __init__(self) -> None:
        # user_id -> list of connections (a user can have multiple tabs)
        self._connections: dict[str, list[ClientConnection]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        project_id: str | None = None,
    ) -> ClientConnection:
        """Accept WebSocket and register the connection."""
        await websocket.accept()
        client = ClientConnection(websocket=websocket, user_id=user_id)
        if project_id:
            client.subscribed_projects.add(project_id)

        async with self._lock:
            self._connections[user_id].append(client)

        logger.info(
            "WS connected: user=%s projects=%s (total=%d)",
            user_id,
            client.subscribed_projects,
            self.connection_count,
        )
        return client

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a connection."""
        async with self._lock:
            conns = self._connections.get(user_id, [])
            self._connections[user_id] = [
                c for c in conns if c.websocket is not websocket
            ]
            if not self._connections[user_id]:
                del self._connections[user_id]

        logger.info("WS disconnected: user=%s (total=%d)", user_id, self.connection_count)

    async def subscribe_project(
        self, websocket: WebSocket, user_id: str, project_id: str
    ) -> None:
        """Add a project subscription for an existing connection."""
        async with self._lock:
            for conn in self._connections.get(user_id, []):
                if conn.websocket is websocket:
                    conn.subscribed_projects.add(project_id)
                    break

    async def broadcast_event(self, event: Event) -> None:
        """Route an event to the appropriate connected clients."""
        dead: list[tuple[str, WebSocket]] = []

        async with self._lock:
            targets = list(self._iter_targets(event))

        for client in targets:
            try:
                await client.websocket.send_json(event.to_dict())
            except Exception:
                dead.append((client.user_id, client.websocket))

        for user_id, ws in dead:
            await self.disconnect(ws, user_id)

    def _iter_targets(self, event: Event):
        """Yield ClientConnection objects that should receive the event."""
        if event.scope == EventScope.GLOBAL:
            for conns in self._connections.values():
                yield from conns
        elif event.scope == EventScope.USER and event.user_id:
            yield from self._connections.get(event.user_id, [])
        elif event.scope == EventScope.PROJECT and event.project_id:
            for conns in self._connections.values():
                for conn in conns:
                    if event.project_id in conn.subscribed_projects:
                        yield conn

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    def active_users(self) -> list[str]:
        return list(self._connections.keys())


# Singleton instance
ws_manager = WebSocketManager()
