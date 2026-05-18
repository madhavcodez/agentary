from __future__ import annotations

import logging
import threading
import time as _time

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..deps import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

# ── Background health cache ─────────────────────────────────────────
# Expensive checks (Qdrant, Celery) run in a background thread every 15s.
# The /health endpoint returns instantly from cache.

_cache: dict = {"status": "ok", "checks": {}, "circuit_breakers": {}}
_cache_lock = threading.Lock()
_bg_started = False


def _run_expensive_checks() -> dict:
    """Run Redis, Qdrant, Celery checks. Called from background thread."""
    checks: dict[str, str] = {}

    # Redis
    try:
        import redis as _redis
        from ..config import settings
        r = _redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        try:
            r.ping()
            checks["redis"] = "ok"
        finally:
            r.close()
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Qdrant
    try:
        from qdrant_client import QdrantClient
        from ..config import settings
        client = QdrantClient(url=settings.qdrant_url, timeout=2, check_compatibility=False)
        try:
            client.get_collections()
            checks["qdrant"] = "ok"
        finally:
            client.close()
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    # Celery — 0.5s max
    try:
        from ..celery_app import celery_app
        ping = celery_app.control.ping(timeout=0.5)
        checks["celery_workers"] = "available" if ping else "unavailable"
    except Exception as e:
        logger.debug("Celery ping failed: %s", e)
        checks["celery_workers"] = "unavailable"

    # Circuit breakers
    try:
        from ..services.circuit_breakers import get_breaker_status
        breakers = get_breaker_status()
    except Exception as e:
        logger.debug("Circuit breaker status unavailable: %s", e)
        breakers = {}

    return {"checks": checks, "circuit_breakers": breakers}


def _background_health_loop() -> None:
    """Runs in a daemon thread — refreshes cache every 15 seconds."""
    while True:
        try:
            result = _run_expensive_checks()
            with _cache_lock:
                _cache["checks"].update(result["checks"])
                _cache["circuit_breakers"] = result["circuit_breakers"]
                all_ok = all(
                    v == "ok" for k, v in _cache["checks"].items()
                    if k not in ("celery_workers",)
                )
                _cache["status"] = "ok" if all_ok else "degraded"
        except (ConnectionError, OSError, RuntimeError) as exc:
            logger.warning("Health check loop error: %s", exc)
        except Exception as exc:
            logger.error("Unexpected health check error: %s", exc)
        _time.sleep(15)


def _ensure_bg_thread() -> None:
    global _bg_started
    if not _bg_started:
        _bg_started = True
        t = threading.Thread(target=_background_health_loop, daemon=True)
        t.start()


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    """Fast health endpoint — Postgres is checked inline, everything else from cache."""
    _ensure_bg_thread()

    # Postgres is fast — always check inline
    try:
        db.execute(text("SELECT 1"))
        pg = "ok"
    except Exception as e:
        pg = f"error: {e}"

    with _cache_lock:
        result = dict(_cache)
        result["checks"] = dict(result.get("checks", {}))
        result["checks"]["postgres"] = pg

    all_ok = all(
        v == "ok" for k, v in result["checks"].items()
        if k not in ("celery_workers",)
    )
    result["status"] = "ok" if all_ok else "degraded"
    return result


@router.get("/health/ready")
def readiness(request: Request) -> dict:
    """Per-subsystem startup readiness.

    Populated by the lifespan handler in ``main.py``. Exposes whether each
    optional subsystem (expert seeding, source registry, scheduler, Redis
    bridge) came up cleanly. Returns ``status: degraded`` if any optional
    subsystem failed; ``status: ok`` only when everything came up.
    """
    readiness = getattr(request.app.state, "readiness", None)
    if readiness is None:
        return {"status": "starting", "subsystems": {}}

    state = dict(readiness.state)
    all_ok = all(v == "ok" for v in state.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "subsystems": state,
    }
