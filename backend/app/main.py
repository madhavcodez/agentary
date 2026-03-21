from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Agentary",
    description="Autonomous research & intelligence platform",
    version="0.2.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from starlette.middleware.base import BaseHTTPMiddleware


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

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── New Agentary routes ──────────────────────────────────────────────
from .api.auth import router as auth_router
from .api.health import router as health_router
from .api.projects import router as projects_router
from .api.missions import router as missions_router
from .api.agents import router as agents_router
from .api.findings import router as findings_router
from .api.datasets import router as datasets_router
from .api.reports import router as reports_router
from .api.voice import router as voice_router
from .api.workflows import router as workflows_router
from .api.monitors import router as monitors_router
from .api.sources import router as sources_router
from .api.knowledge_base import router as kb_router
from .api.live_feed import router as live_feed_router
from .api.contacts import router as contacts_router
from .api.research import router as research_router
from .api.analytics import router as analytics_router
from .api.policies import router as policies_router
from .api.webhooks import router as webhooks_router
from .voice.outbound.server import router as outbound_router

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(projects_router)
app.include_router(missions_router)
app.include_router(agents_router)
app.include_router(findings_router)
app.include_router(datasets_router)
app.include_router(reports_router)
app.include_router(voice_router)
app.include_router(workflows_router)
app.include_router(monitors_router)
app.include_router(sources_router)
app.include_router(kb_router)
app.include_router(live_feed_router)
app.include_router(contacts_router)
app.include_router(research_router)
app.include_router(analytics_router)
app.include_router(policies_router)
app.include_router(webhooks_router)
app.include_router(outbound_router)
