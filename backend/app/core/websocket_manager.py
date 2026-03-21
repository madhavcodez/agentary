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
    def __init__(self) -> None:
        self._connections: dict[str, list[ClientConnection]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        project_id: str | None = None,
    ) -> ClientConnection:
        await websocket.accept()
        client = ClientConnection(websocket=websocket, user_id=user_id)
        if project_id:
            client.subscribed_projects.add(project_id)

        async with self._lock:
            self._connections[user_id].append(client)

        logger.info("WS connected: user=%s (total=%d)", user_id, self.connection_count)
        return client

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
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
        async with self._lock:
            for conn in self._connections.get(user_id, []):
                if conn.websocket is websocket:
                    conn.subscribed_projects.add(project_id)
                    break

    async def broadcast_to_clients(self, event_dict: dict[str, Any]) -> None:
        """Route an event dict to the appropriate connected clients."""
        dead: list[tuple[str, WebSocket]] = []
        project_id = event_dict.get("project_id")
        user_id = event_dict.get("user_id")

        async with self._lock:
            targets: list[ClientConnection] = []
            if project_id:
                for conns in self._connections.values():
                    for conn in conns:
                        if project_id in conn.subscribed_projects:
                            targets.append(conn)
            elif user_id:
                targets.extend(self._connections.get(user_id, []))
            else:
                for conns in self._connections.values():
                    targets.extend(conns)

        for client in targets:
            try:
                await client.websocket.send_json(event_dict)
            except Exception:
                dead.append((client.user_id, client.websocket))

        for uid, ws in dead:
            await self.disconnect(ws, uid)

    @property
    def connection_count(self) -> int:
        return sum(len(conns) for conns in self._connections.values())

    def active_users(self) -> list[str]:
        return list(self._connections.keys())


# Singleton instance
ws_manager = WebSocketManager()
