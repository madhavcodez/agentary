"""Redis pub/sub bridge for cross-process event delivery to WebSocket clients."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from ..config import settings

logger = logging.getLogger(__name__)

CHANNEL = "agentary:events"
CHANNEL_PREFIX = f"{CHANNEL}:"


class RedisBridge:
    """Bridges Redis pub/sub with the WebSocket layer.

    Subscribes to ``agentary:events`` channels and forwards incoming
    messages to the appropriate WebSocket connections via
    :class:`WebSocketManager`.
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._subscriber_task: asyncio.Task | None = None

    # ── Lifecycle ────────────────────────────────────────────────────

    async def start(self, redis_url: str | None = None) -> None:
        """Connect to Redis and begin listening for events."""
        url = redis_url or settings.redis_url
        self._redis = aioredis.from_url(url, decode_responses=True)
        self._subscriber_task = asyncio.create_task(self._subscribe_loop())
        logger.info("RedisBridge started (url=%s)", url)

    async def stop(self) -> None:
        """Cancel the subscriber task and close the Redis connection."""
        if self._subscriber_task is not None:
            self._subscriber_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._subscriber_task
            self._subscriber_task = None

        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

        logger.info("RedisBridge stopped")

    # ── Publishing ───────────────────────────────────────────────────

    async def publish(
        self,
        event_type: str,
        data: dict[str, Any],
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Publish a message to the appropriate Redis channel."""
        if self._redis is None:
            logger.debug("RedisBridge not started, skipping publish")
            return

        if project_id:
            channel = f"{CHANNEL_PREFIX}project:{project_id}"
        elif user_id:
            channel = f"{CHANNEL_PREFIX}user:{user_id}"
        else:
            channel = f"{CHANNEL_PREFIX}global"

        payload = {
            "event_type": event_type,
            "data": data,
            "project_id": project_id,
            "user_id": user_id,
        }

        try:
            await self._redis.publish(channel, json.dumps(payload, default=str))
        except Exception as exc:
            logger.warning("Failed to publish event to Redis: %s", exc)

    # ── Subscription loop ────────────────────────────────────────────

    async def _subscribe_loop(self) -> None:
        """Long-lived coroutine that listens for pub/sub messages and
        forwards them to WebSocket clients via :data:`ws_manager`."""
        from .websocket_manager import ws_manager

        while True:
            try:
                if self._redis is None:
                    break

                pubsub = self._redis.pubsub()
                await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
                logger.info("Redis subscriber started on %s*", CHANNEL_PREFIX)

                async for message in pubsub.listen():
                    if message["type"] not in ("pmessage",):
                        continue
                    try:
                        event_data = json.loads(message["data"])
                        await ws_manager.broadcast_to_clients(event_data)
                    except Exception as exc:
                        logger.warning("Failed to process Redis message: %s", exc)

            except asyncio.CancelledError:
                logger.info("Redis subscriber cancelled")
                break
            except Exception as exc:
                logger.error("Redis subscriber error, reconnecting in 3s: %s", exc)
                await asyncio.sleep(3)


# Singleton instance
redis_bridge = RedisBridge()


# ── Convenience function used by EventBus.broadcast ──────────────


async def publish_event(event) -> None:
    """Publish an :class:`Event` via the global :data:`redis_bridge`.

    Falls back to a direct Redis publish when the bridge has not been
    started (keeps the same behaviour as the original module-level helper).
    """
    if redis_bridge._redis is not None:
        d = event.to_dict()
        await redis_bridge.publish(
            event_type=d.get("event_type", ""),
            data=d.get("data", {}),
            project_id=d.get("project_id"),
            user_id=d.get("user_id"),
        )
        return

    # Fallback: one-shot publish without a running bridge
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
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
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning("Failed to publish event to Redis: %s", exc)


# ── Backward-compatible helpers used by main.py lifespan ─────────


async def subscribe_and_forward(ws_manager) -> None:
    """Subscribe to all agentary event channels and forward to WebSocket clients.

    Runs as a long-lived coroutine -- launch via ``asyncio.create_task``
    in the app lifespan.  Delegates to the singleton :data:`redis_bridge`.
    """

    # Ensure the bridge has a Redis connection
    if redis_bridge._redis is None:
        redis_bridge._redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

    while True:
        try:
            pubsub = redis_bridge._redis.pubsub()
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
    """Close the Redis connection held by the global bridge."""
    await redis_bridge.stop()
