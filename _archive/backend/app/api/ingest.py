from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..database import SessionLocal
from ..models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingest"])

_ingest_status: dict[str, str | int] = {"status": "idle", "last_count": 0}


def _run_ingest_background(user_id):
    """Run ingest in a background thread with its own DB session."""
    from ..services.ingest.runner import run_all_connectors

    _ingest_status["status"] = "running"
    db = SessionLocal()
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        count = loop.run_until_complete(run_all_connectors(db, user_id=user_id))
        loop.close()
        _ingest_status["status"] = "completed"
        _ingest_status["last_count"] = count
        logger.info("Background ingest completed: %d new opportunities", count)
    except Exception as e:
        _ingest_status["status"] = f"error: {e}"
        logger.error("Background ingest failed: %s", e)
    finally:
        db.close()


@router.post("/run")
async def run_ingest(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    if _ingest_status["status"] == "running":
        return {"status": "already_running", "detail": "Ingest is already in progress"}

    background_tasks.add_task(_run_ingest_background, user.id)
    return {"status": "started", "detail": "Ingest started in background. Check /ingest/status for progress."}


@router.get("/status")
def ingest_status(user: User = Depends(get_current_user)):
    return _ingest_status
