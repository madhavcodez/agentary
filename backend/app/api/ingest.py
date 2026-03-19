from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_db

router = APIRouter(prefix="/ingest", tags=["ingest"])

_ingest_status: dict[str, str | int] = {"status": "idle", "last_count": 0}


@router.post("/run")
async def run_ingest(db: Session = Depends(get_db)):
    from ..services.ingest.runner import run_all_connectors
    _ingest_status["status"] = "running"
    try:
        count = await run_all_connectors(db)
        _ingest_status["status"] = "completed"
        _ingest_status["last_count"] = count
        return {"status": "completed", "opportunities_ingested": count}
    except Exception as e:
        _ingest_status["status"] = f"error: {e}"
        return {"status": "error", "detail": str(e)}


@router.get("/status")
def ingest_status():
    return _ingest_status
