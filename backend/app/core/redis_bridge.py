"""Redis pub/sub bridge for cross-process event delivery to WebSocket clients."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

import redis.asyncio as aioredis

from ..config import settings

if TYPE_CHECKING:
    from .websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "agentary:events:"

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_client


async def publish_event(event) -> None:
    """Publish an event to the appropriate Redis channel."""
    try:
        r = await get_redis()
        d = event.to_dict()
        project_id = d.get("project_id")
        user_id = d.get("user_id")

        if project_id:
            channel = f"{CHANNEL_PREFIX}project:{project_id}"
        elif user_id:
            channel = f"{CHANNEL_PREFIX}user:{user_id}"
        else:
            channel = f"{CHANNEL_PREFIX}global"

        await r.publish(channel, json.dumps(d, default=str))
    except Exception as exc:
        logger.warning("Failed to publish event to Redis: %s", exc)


async def subscribe_and_forward(ws_manager: WebSocketManager) -> None:
    """Subscribe to all agentary event channels and forward to WebSocket clients.

    Runs as a long-lived coroutine — launch via asyncio.create_task in app lifespan.
    """
    while True:
        try:
            r = await get_redis()
            pubsub = r.pubsub()
            await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
            logger.info("Redis subscriber started on %s*", CHANNEL_PREFIX)

            async for message in pubsub.listen():
                if message["type"] not in ("pmessage",):
                    continue
                try:
                    data = json.loads(message["data"])
                    await ws_manager.broadcast_to_clients(data)
                except Exception as exc:
                    logger.warning("Failed to process Redis message: %s", exc)

        except asyncio.CancelledError:
            logger.info("Redis subscriber cancelled")
            break
        except Exception as exc:
            logger.error("Redis subscriber error, reconnecting in 3s: %s", exc)
            await asyncio.sleep(3)


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
