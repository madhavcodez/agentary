"""Per-mission Gemini call budget for STORM.

Agentary has already been burned once by uncapped LLM fan-out (DeerFlow was
pulled out of the politics briefing after a single run consumed >6 Gemini
calls and triggered free-tier quota failures). STORM multiplies calls by
perspectives x sections x refinement passes, so every call must pass through
a hard cap.

The counter lives in Redis so concurrent workers synthesizing different
sections in parallel share the same budget view. If Redis is unreachable
the counter degrades gracefully to in-process state and logs a warning.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Defaults are intentionally tight — tune via settings, not here.
DEFAULT_MAX_FLASH_CALLS = 10
DEFAULT_MAX_PRO_CALLS = 8
_REDIS_KEY_PREFIX = "storm:budget"
_REDIS_TTL_SECONDS = 60 * 60  # 1 hour, well past any reasonable mission run

_redis_client: Any | None = None


class StormBudgetExceeded(RuntimeError):
    """Raised when incrementing the counter would exceed the cap."""


def _get_redis() -> Any | None:
    """Lazy Redis client. Returns None if the client cannot be created."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:  # pragma: no cover — environment-dependent
        import redis  # type: ignore[import-not-found]

        from ...config import settings

        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        _redis_client.ping()
    except Exception as exc:
        logger.warning("StormBudget: Redis unavailable, falling back to in-process (%s)", exc)
        _redis_client = None
    return _redis_client


class StormBudget:
    """Enforce per-mission Gemini call caps across workers.

    Usage:
        budget = StormBudget(mission_id="...")
        budget.inc("flash")   # raises StormBudgetExceeded when over cap
        budget.inc("pro")

    Caps are read from settings at construction time; override via env:
        STORM_MAX_FLASH_CALLS (default 10)
        STORM_MAX_PRO_CALLS   (default 8)
    """

    def __init__(
        self,
        *,
        mission_id: str,
        max_flash_calls: int | None = None,
        max_pro_calls: int | None = None,
    ) -> None:
        self.mission_id = mission_id
        self.max_flash_calls = max_flash_calls or int(
            os.environ.get("STORM_MAX_FLASH_CALLS", DEFAULT_MAX_FLASH_CALLS)
        )
        self.max_pro_calls = max_pro_calls or int(
            os.environ.get("STORM_MAX_PRO_CALLS", DEFAULT_MAX_PRO_CALLS)
        )
        self._fallback: dict[str, int] = {"flash": 0, "pro": 0}

    def _key(self, kind: str) -> str:
        return f"{_REDIS_KEY_PREFIX}:{self.mission_id}:{kind}"

    def _get(self, kind: str) -> int:
        client = _get_redis()
        if client is None:
            return self._fallback.get(kind, 0)
        try:
            raw = client.get(self._key(kind))
            return int(raw) if raw is not None else 0
        except Exception as exc:
            logger.warning("StormBudget._get fallback: %s", exc)
            return self._fallback.get(kind, 0)

    def inc(self, kind: str) -> None:
        """Increment counter for `kind` (``"flash"`` or ``"pro"``).

        Raises :class:`StormBudgetExceeded` when the resulting count exceeds
        the configured cap for that kind.
        """
        if kind not in ("flash", "pro"):
            raise ValueError(f"Unknown budget kind: {kind!r}")

        cap = self.max_flash_calls if kind == "flash" else self.max_pro_calls
        client = _get_redis()
        if client is None:
            new_val = self._fallback[kind] + 1
            self._fallback[kind] = new_val
        else:
            try:
                new_val = int(client.incr(self._key(kind)))
                client.expire(self._key(kind), _REDIS_TTL_SECONDS)
            except Exception as exc:
                logger.warning("StormBudget.inc fallback: %s", exc)
                self._fallback[kind] = self._fallback.get(kind, 0) + 1
                new_val = self._fallback[kind]

        if new_val > cap:
            raise StormBudgetExceeded(
                f"mission={self.mission_id} kind={kind} count={new_val} cap={cap}"
            )

    @property
    def flash_calls(self) -> int:
        return self._get("flash")

    @property
    def pro_calls(self) -> int:
        return self._get("pro")

    def snapshot(self) -> dict[str, int]:
        """Return current counts for telemetry emission."""
        return {
            "flash_calls": self.flash_calls,
            "pro_calls": self.pro_calls,
            "max_flash_calls": self.max_flash_calls,
            "max_pro_calls": self.max_pro_calls,
        }
