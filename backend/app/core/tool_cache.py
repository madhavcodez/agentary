"""Fail-open Redis cache for LLM-tool invocations.

The Exa, Gemini, and web-scraper tools each cost money or rate-limited
quota every call. When two missions investigate overlapping topics the
same queries fire repeatedly. A short-TTL cache keyed on (tool, params)
absorbs duplicates with no behavioural change for the caller.

Design choices
- ``fail open``: any Redis failure returns ``None``/no-op. Tool calls
  never block on cache infrastructure.
- ``deterministic keys`` from sorted JSON parameters so cosmetic ordering
  doesn't fragment the cache.
- ``per-call TTL`` because Exa results stale faster than web scrapes.
- ``serialisation via json`` only — anything not JSON-serialisable is
  rejected, surfacing bugs early instead of silently failing.

Operators can disable the cache entirely by setting ``TOOL_CACHE_ENABLED=0``
in env without code changes.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as aioredis

from ..config import settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "tool_cache"


class ToolCache:
    """Tool-result cache backed by Redis.

    Stateless from the caller's perspective. The connection is lazily
    established on first use so import is cheap and a Redis outage doesn't
    cascade into a startup failure.
    """

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._enabled = os.getenv("TOOL_CACHE_ENABLED", "1") == "1"
        self._connected = False

    async def _ensure_connection(self) -> bool:
        """Lazy-connect to Redis on first use. Returns True if available."""
        if not self._enabled:
            return False
        if self._connected:
            return self._redis is not None
        try:
            client = aioredis.from_url(settings.redis_url, decode_responses=True)
            await client.ping()
            self._redis = client
            self._connected = True
            return True
        except Exception as exc:
            logger.warning("ToolCache: Redis unavailable, running without cache: %s", exc)
            self._redis = None
            self._connected = True  # mark as attempted so we don't retry every call
            return False

    @staticmethod
    def _make_key(tool: str, params: dict[str, Any]) -> str:
        canonical = json.dumps({"tool": tool, "params": params}, sort_keys=True, default=str)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
        return f"{_KEY_PREFIX}:{tool}:{digest}"

    async def get(self, tool: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Return a cached result or None."""
        if not await self._ensure_connection() or self._redis is None:
            return None
        try:
            raw = await self._redis.get(self._make_key(tool, params))
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.debug("tool_cache get failed for %s: %s", tool, exc)
            return None

    async def set(
        self,
        tool: str,
        params: dict[str, Any],
        value: dict[str, Any],
        ttl_seconds: int,
    ) -> None:
        """Store a result. Silent on Redis errors."""
        if not await self._ensure_connection() or self._redis is None:
            return
        try:
            payload = json.dumps(value, default=str)
        except (TypeError, ValueError) as exc:
            # Surface bugs early — better to skip cache than to crash.
            logger.warning("tool_cache: refusing to cache non-serialisable %s: %s", tool, exc)
            return
        try:
            await self._redis.setex(self._make_key(tool, params), ttl_seconds, payload)
        except Exception as exc:
            logger.debug("tool_cache set failed for %s: %s", tool, exc)

    async def cached(
        self,
        tool: str,
        params: dict[str, Any],
        ttl_seconds: int,
        fetch: Callable[[], Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Return cached value or fetch + store.

        Adds ``{"cached": True}`` to the returned dict on hit so callers can
        log/meter cache effectiveness without an extra round-trip.
        """
        hit = await self.get(tool, params)
        if hit is not None:
            hit["cached"] = True
            return hit
        result = await fetch()
        # Only cache successful results — error envelopes should not be cached
        # because the next attempt might succeed.
        if isinstance(result, dict) and result.get("status") == "success":
            await self.set(tool, params, result, ttl_seconds)
        return result


# Module-level singleton — same lifetime as the process.
tool_cache = ToolCache()
