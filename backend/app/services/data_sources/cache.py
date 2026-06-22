"""Redis caching for expensive data source queries."""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis

from ...config import settings
from .base_connector import SourceResult

logger = logging.getLogger(__name__)


class SourceCache:
    def __init__(self):
        self._redis: aioredis.Redis | None = None
        self._available = False

    async def connect(self):
        try:
            self._redis = aioredis.from_url(
                settings.redis_url, decode_responses=True,
            )
            await self._redis.ping()
            self._available = True
            logger.info("Source cache connected to Redis")
        except Exception as e:
            logger.warning("Redis unavailable for source cache: %s", e)
            self._available = False

    def make_key(self, provider: str, method: str, params: dict) -> str:
        raw = json.dumps(
            {"provider": provider, "method": method, **params}, sort_keys=True,
        )
        return f"source_cache:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    async def get(self, key: str) -> SourceResult | None:
        if not self._available or not self._redis:
            return None
        try:
            cached = await self._redis.get(key)
            if cached:
                data = json.loads(cached)
                return SourceResult(
                    data=data["data"],
                    raw_response=None,
                    total_results=data["total_results"],
                    source_name=data["source_name"],
                    source_url=data.get("source_url"),
                    cost_usd=0.0,
                    cached=True,
                    metadata=data.get("metadata", {}),
                )
        except Exception as e:
            logger.debug("Cache get error: %s", e)
        return None

    async def set(self, key: str, result: SourceResult, ttl_seconds: int):
        if not self._available or not self._redis:
            return
        try:
            payload = json.dumps(result.to_dict(), default=str)
            await self._redis.setex(key, ttl_seconds, payload)
        except Exception as e:
            logger.debug("Cache set error: %s", e)

    async def cached_query(
        self,
        cache_key: str,
        ttl: int,
        fetch_fn: Callable[[], Awaitable[SourceResult]],
    ) -> SourceResult:
        cached = await self.get(cache_key)
        if cached:
            return cached
        result = await fetch_fn()
        await self.set(cache_key, result, ttl)
        return result


# Singleton instance
source_cache = SourceCache()
