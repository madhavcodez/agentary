"""Tests for the WebSocket connection manager."""

from unittest.mock import AsyncMock

import pytest

from app.core.websocket_manager import WebSocketManager


def make_mock_ws():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect_and_disconnect():
    mgr = WebSocketManager()
    ws = make_mock_ws()

    await mgr.connect(ws, "user-1")
    assert mgr.connection_count == 1
    assert "user-1" in mgr.active_users()

    await mgr.disconnect(ws, "user-1")
    assert mgr.connection_count == 0


@pytest.mark.asyncio
async def test_broadcast_global():
    mgr = WebSocketManager()
    ws1 = make_mock_ws()
    ws2 = make_mock_ws()

    await mgr.connect(ws1, "user-1")
    await mgr.connect(ws2, "user-2")

    event = {"event_type": "system.status", "data": {"status": "ok"}}
    await mgr.broadcast_to_clients(event)

    ws1.send_json.assert_called_once_with(event)
    ws2.send_json.assert_called_once_with(event)


@pytest.mark.asyncio
async def test_broadcast_user_scoped():
    mgr = WebSocketManager()
    ws1 = make_mock_ws()
    ws2 = make_mock_ws()

    await mgr.connect(ws1, "user-1")
    await mgr.connect(ws2, "user-2")

    event = {"event_type": "monitor.alert", "user_id": "user-1", "data": {}}
    await mgr.broadcast_to_clients(event)

    ws1.send_json.assert_called_once_with(event)
    ws2.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_project_scoped():
    mgr = WebSocketManager()
    ws1 = make_mock_ws()
    ws2 = make_mock_ws()

    await mgr.connect(ws1, "user-1")
    await mgr.connect(ws2, "user-2")
    await mgr.subscribe_project(ws1, "user-1", "project-abc")

    event = {"event_type": "finding.created", "project_id": "project-abc", "data": {}}
    await mgr.broadcast_to_clients(event)

    ws1.send_json.assert_called_once_with(event)
    ws2.send_json.assert_not_called()


@pytest.mark.asyncio
async def test_dead_connection_cleanup():
    mgr = WebSocketManager()
    ws = make_mock_ws()
    ws.send_json.side_effect = Exception("connection closed")

    await mgr.connect(ws, "user-1")
    assert mgr.connection_count == 1

    await mgr.broadcast_to_clients({"event_type": "test", "data": {}})
    assert mgr.connection_count == 0


@pytest.mark.asyncio
async def test_multiple_connections_per_user():
    mgr = WebSocketManager()
    ws1 = make_mock_ws()
    ws2 = make_mock_ws()

    await mgr.connect(ws1, "user-1")
    await mgr.connect(ws2, "user-1")
    assert mgr.connection_count == 2

    await mgr.disconnect(ws1, "user-1")
    assert mgr.connection_count == 1
