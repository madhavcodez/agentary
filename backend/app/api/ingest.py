from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.user import User

router = APIRouter(prefix="/ingest", tags=["ingest"])

_ingest_status: dict[str, str | int] = {"status": "idle", "last_count": 0}


@router.post("/run")
async def run_ingest(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from ..services.ingest.runner import run_all_connectors
    _ingest_status["status"] = "running"
    try:
        count = await run_all_connectors(db, user_id=user.id)
        _ingest_status["status"] = "completed"
        _ingest_status["last_count"] = count
        return {"status": "completed", "opportunities_ingested": count}
    except Exception as e:
        _ingest_status["status"] = f"error: {e}"
        return {"status": "error", "detail": str(e)}


@router.get("/status")
def ingest_status(user: User = Depends(get_current_user)):
    return _ingest_status
