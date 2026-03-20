from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="SecretAIRY",
    description="AI Chief-of-Staff — opportunity scout, research engine, and voice assistant",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
from .voice.outbound.server import router as outbound_router

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
app.include_router(outbound_router)
