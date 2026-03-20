from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .database import init_db
from .services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="SecretAIRY",
    description="AI Chief-of-Staff — opportunity scout, research engine, and voice assistant",
    version="0.1.0",
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

from .api.auth import router as auth_router
from .api.health import router as health_router
from .api.profile import router as profile_router
from .api.opportunities import router as opportunities_router
from .api.ingest import router as ingest_router
from .api.matches import router as matches_router
from .api.dossiers import router as dossiers_router
from .api.policies import router as policies_router
from .api.contacts import router as contacts_router
from .api.campaigns import router as campaigns_router
from .api.research import router as research_router
from .api.autopilot import router as autopilot_router
from .api.analytics import router as analytics_router
from .voice.outbound.server import router as outbound_router
from .api.webhooks import router as webhooks_router
from .api.scout import router as scout_router

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(profile_router)
app.include_router(opportunities_router)
app.include_router(ingest_router)
app.include_router(matches_router)
app.include_router(dossiers_router)
app.include_router(policies_router)
app.include_router(contacts_router)
app.include_router(campaigns_router)
app.include_router(research_router)
app.include_router(autopilot_router)
app.include_router(analytics_router)
app.include_router(outbound_router)
app.include_router(webhooks_router)
app.include_router(scout_router)
