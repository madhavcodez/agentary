from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .core.logging_config import setup_logging
from .database import SessionLocal, init_db

# Activate structured JSON logging before anything else logs
setup_logging()

logger = logging.getLogger(__name__)


class SubsystemReadiness:
    """Track which startup subsystems came up. Exposed at /health/ready.

    Required subsystems failing propagate the exception and abort startup;
    optional subsystems degrade but surface their state so operators can
    see the partial outage instead of believing the boot was clean.
    """

    def __init__(self) -> None:
        self.state: dict[str, str] = {}

    def mark(self, name: str, status: str) -> None:
        self.state[name] = status
        logger.info("subsystem %s: %s", name, status)

    def required(self, name: str) -> "_SubsystemContext":
        return _SubsystemContext(self, name, required=True)

    def optional(self, name: str) -> "_SubsystemContext":
        return _SubsystemContext(self, name, required=False)


class _SubsystemContext:
    def __init__(self, readiness: SubsystemReadiness, name: str, *, required: bool) -> None:
        self._readiness = readiness
        self._name = name
        self._required = required

    def __enter__(self) -> "_SubsystemContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is None:
            self._readiness.mark(self._name, "ok")
            return False
        if self._required:
            self._readiness.mark(self._name, f"failed: {exc}")
            logger.critical("required subsystem %s failed: %s", self._name, exc)
            return False  # re-raise; startup aborts
        self._readiness.mark(self._name, f"degraded: {exc}")
        logger.warning("optional subsystem %s degraded: %s", self._name, exc)
        return True  # swallow; app keeps booting


@asynccontextmanager
async def lifespan(app: FastAPI):
    readiness = SubsystemReadiness()
    app.state.readiness = readiness

    # Required: if the DB isn't reachable, we can't serve anything useful.
    with readiness.required("database"):
        init_db()

    # Optional: expert seeding. Uses a context-managed session so we never
    # leak a connection on early-exit paths.
    with readiness.optional("expert_seeding"):
        from .services.crews.expert_registry import seed_builtin_experts

        with SessionLocal() as db:
            seed_builtin_experts(db)

    # Optional: source registry. If init fails, ``request.app.state`` will
    # not have ``source_registry``; data-source routes already handle that.
    with readiness.optional("source_registry"):
        from .services.data_sources.source_registry import create_source_registry

        app.state.source_registry = create_source_registry(settings)

    # Optional: scheduler. We capture the stop handle in a closure so the
    # shutdown branch can always call something — without the explicit None
    # binding we'd hit UnboundLocalError on the failure path.
    stop_scheduler = lambda: None  # noqa: E731
    with readiness.optional("scheduler"):
        from .services.scheduler import start_scheduler
        from .services.scheduler import stop_scheduler as _stop_scheduler

        start_scheduler()
        stop_scheduler = _stop_scheduler

    # Optional: Redis → WebSocket bridge. Failure means dashboard event
    # streaming degrades to polling, but the rest of the API works.
    redis_task: asyncio.Task | None = None
    close_redis = None
    with readiness.optional("redis_bridge"):
        from .core.redis_bridge import close_redis as _close_redis
        from .core.redis_bridge import subscribe_and_forward
        from .core.websocket_manager import ws_manager

        redis_task = asyncio.create_task(
            subscribe_and_forward(ws_manager), name="redis-ws-bridge"
        )
        close_redis = _close_redis

    yield

    # ── Shutdown ──────────────────────────────────────────────────────
    if redis_task is not None:
        redis_task.cancel()
        try:
            await redis_task
        except (asyncio.CancelledError, Exception):
            pass
    if close_redis is not None:
        try:
            await close_redis()
        except Exception:
            logger.warning("close_redis raised during shutdown", exc_info=True)
    try:
        stop_scheduler()
    except Exception:
        logger.warning("stop_scheduler raised during shutdown", exc_info=True)


from .core.rate_limiter import limiter

app = FastAPI(
    title="Agentary",
    description="Autonomous research & intelligence platform",
    version="0.2.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


from .config import settings
from .core.correlation import CorrelationMiddleware

# Middleware is applied in reverse registration order (last registered runs first).
# Register CorrelationMiddleware last so it executes first on every request.
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)
app.add_middleware(CorrelationMiddleware)


@app.get("/")
def root():
    return {
        "name": "Agentary",
        "description": "Autonomous research & intelligence platform",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
    }


# ── Agentary routes ──────────────────────────────────────────────────
from .api.auth import router as auth_router
from .api.health import router as health_router
from .api.projects import router as projects_router
from .api.missions import router as missions_router
from .api.agents import router as agents_router
from .api.experts import router as experts_router
from .api.crews import router as crews_router
from .api.findings import router as findings_router
from .api.datasets import router as datasets_router
from .api.workflows import router as workflows_router
from .api.workflow_templates import router as workflow_templates_router
from .api.reports import router as reports_router
from .api.export import router as export_router
from .api.shared import router as shared_router
from .api.voice import router as voice_router
from .api.voice_sessions import router as voice_sessions_router
from .api.voice_templates import router as voice_templates_router
from .api.voice_batch import router as voice_batch_router
from .api.voice_webhooks import router as voice_webhooks_router
from .api.monitors import router as monitors_router
from .api.alerts import router as alerts_router
from .api.entities import router as entities_router
from .api.entity_collections import router as entity_collections_router
from .api.data_sources import router as data_sources_router
from .api.sources import router as sources_router
from .api.knowledge_base import router as kb_router
from .api.live_feed import router as live_feed_router
from .api.analytics import router as analytics_router
from .api.contacts import router as contacts_router
from .api.research import router as research_router
from .api.policies import router as policies_router
from .api.webhooks import router as webhooks_router
from .voice.outbound.server import router as outbound_router
from .api.run_steps import router as run_steps_router
from .api.signals import router as signals_router
from .api.insights import router as insights_router
from .api.recommendations import router as recommendations_router
from .api.entity_aliases import router as entity_aliases_router
from .api.entity_relationships import router as entity_relationships_router
from .api.admin import router as admin_router
from .api.actions import router as actions_router

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(projects_router)
app.include_router(missions_router)
app.include_router(agents_router)
app.include_router(experts_router)
app.include_router(crews_router)
app.include_router(findings_router)
app.include_router(datasets_router)
app.include_router(workflows_router)
app.include_router(workflow_templates_router)
app.include_router(reports_router)
app.include_router(export_router)
app.include_router(shared_router)
app.include_router(voice_router)
app.include_router(voice_sessions_router)
app.include_router(voice_templates_router)
app.include_router(voice_batch_router)
app.include_router(voice_webhooks_router)
app.include_router(monitors_router)
app.include_router(alerts_router)
app.include_router(entities_router)
app.include_router(entity_collections_router)
app.include_router(data_sources_router)
app.include_router(sources_router)
app.include_router(kb_router)
app.include_router(live_feed_router)
app.include_router(analytics_router)
app.include_router(contacts_router)
app.include_router(research_router)
app.include_router(policies_router)
app.include_router(webhooks_router)
app.include_router(outbound_router)
app.include_router(run_steps_router)
app.include_router(signals_router)
app.include_router(insights_router)
app.include_router(recommendations_router)
app.include_router(entity_aliases_router)
app.include_router(entity_relationships_router)
app.include_router(admin_router)
app.include_router(actions_router)
