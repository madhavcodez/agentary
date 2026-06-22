"""WebSocket connection manager with project/user-scoped routing."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class ClientConnection:
    websocket: WebSocket
    user_id: str
    subscribed_projects: set[str] = field(default_factory=set)


class WebSocketManager:
    """Thread-safe manager for active WebSocket connections keyed by user_id.

    Provides user-scoped, project-scoped, and global broadcast capabilities.
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[ClientConnection]] = defaultdict(list)
        self._lock = asyncio.Lock()

    # ── Connection lifecycle ─────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        project_id: str | None = None,
    ) -> ClientConnection:
        """Accept a WebSocket and register it under *user_id*."""
        await websocket.accept()
        client = ClientConnection(websocket=websocket, user_id=user_id)
        if project_id:
            client.subscribed_projects.add(project_id)

        async with self._lock:
            self._connections[user_id].append(client)

        logger.info("WS connected: user=%s (total=%d)", user_id, self.connection_count)
        return client

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a specific WebSocket for *user_id*, cleaning up gracefully."""
        async with self._lock:
            conns = self._connections.get(user_id, [])
            self._connections[user_id] = [c for c in conns if c.websocket is not websocket]
            if not self._connections[user_id]:
                del self._connections[user_id]

        logger.info("WS disconnected: user=%s (total=%d)", user_id, self.connection_count)

    # ── Project subscriptions ────────────────────────────────────────

    async def subscribe_project(self, websocket: WebSocket, user_id: str, project_id: str) -> None:
        """Add a project subscription to an existing connection."""
        async with self._lock:
            for conn in self._connections.get(user_id, []):
                if conn.websocket is websocket:
                    conn.subscribed_projects.add(project_id)
                    break

    # ── Sending helpers ──────────────────────────────────────────────

    async def send_to_user(self, user_id: str, data: dict[str, Any]) -> None:
        """Send *data* to every connection belonging to *user_id*."""
        dead: list[tuple[str, WebSocket]] = []

        async with self._lock:
            targets = list(self._connections.get(user_id, []))

        for client in targets:
            try:
                await client.websocket.send_json(data)
            except Exception:
                dead.append((client.user_id, client.websocket))

        for uid, ws in dead:
            await self.disconnect(ws, uid)

    async def broadcast(self, data: dict[str, Any]) -> None:
        """Send *data* to every connected client regardless of user or project."""
        dead: list[tuple[str, WebSocket]] = []

        async with self._lock:
            targets = [conn for conns in self._connections.values() for conn in conns]

        for client in targets:
            try:
                await client.websocket.send_json(data)
            except Exception:
                dead.append((client.user_id, client.websocket))

        for uid, ws in dead:
            await self.disconnect(ws, uid)

    async def broadcast_to_project(self, project_id: str, data: dict[str, Any]) -> None:
        """Send *data* to every client subscribed to *project_id*."""
        dead: list[tuple[str, WebSocket]] = []

        async with self._lock:
            targets = [
                conn
                for conns in self._connections.values()
                for conn in conns
                if project_id in conn.subscribed_projects
            ]

        for client in targets:
            try:
                await client.websocket.send_json(data)
            except Exception:
                dead.append((client.user_id, client.websocket))

        for uid, ws in dead:
            await self.disconnect(ws, uid)

    async def broadcast_to_clients(self, event_dict: dict[str, Any]) -> None:
        """Route an event dict to the appropriate connected clients.

        Dispatches to project-scoped, user-scoped, or global broadcast
        depending on the fields present in *event_dict*.
        """
        project_id = event_dict.get("project_id")
        user_id = event_dict.get("user_id")

        if project_id:
            await self.broadcast_to_project(project_id, event_dict)
        elif user_id:
            await self.send_to_user(user_id, event_dict)
        else:
            await self.broadcast(event_dict)

    # ── Introspection ────────────────────────────────────────────────

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    def active_users(self) -> list[str]:
        return list(self._connections.keys())


# Singleton instance
ws_manager = WebSocketManager()
