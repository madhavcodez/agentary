from __future__ import annotations
from .celery_app import celery_app


@celery_app.task(name="app.tasks.voice_tasks.initiate_call")
def initiate_call(voice_extraction_id: str, target_index: int) -> dict:
    """Initiate a voice call. Stub."""
    return {"status": "not_implemented"}
