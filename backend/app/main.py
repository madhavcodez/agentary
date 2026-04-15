from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .core.logging_config import setup_logging
from .database import init_db

# Activate structured JSON logging before anything else logs
setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Seed built-in expert agents
    try:
        from .services.crews.expert_registry import seed_builtin_experts
        from .database import get_session
        db = next(get_session())
        try:
            seed_builtin_experts(db)
            logger.info("Expert agents seeded")
        except Exception as exc:
            logger.warning("Expert agent seeding failed: %s", exc)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Expert registry not available: %s", exc)

    # Initialize SourceRegistry
    try:
        from .services.data_sources.source_registry import create_source_registry
        app.state.source_registry = create_source_registry(settings)
        logger.info("SourceRegistry initialized")
    except Exception as exc:
        logger.warning("SourceRegistry init failed: %s", exc)

    # Start scheduler
    try:
        from .services.scheduler import start_scheduler, stop_scheduler
        start_scheduler()
    except Exception as exc:
        logger.warning("Scheduler start failed: %s", exc)
        stop_scheduler = lambda: None

    # Start Redis → WebSocket bridge
    redis_task = None
    try:
        from .core.redis_bridge import subscribe_and_forward, close_redis
        from .core.websocket_manager import ws_manager
        redis_task = asyncio.create_task(subscribe_and_forward(ws_manager))
    except Exception as exc:
        logger.warning("Redis bridge not started: %s", exc)

    yield

    if redis_task:
        redis_task.cancel()
        try:
            await close_redis()
        except Exception:
            pass
    try:
        stop_scheduler()
    except Exception:
        pass


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
