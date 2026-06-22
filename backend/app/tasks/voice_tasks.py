"""Celery tasks for voice extraction: call execution, post-processing, batch."""

from __future__ import annotations

import asyncio
import logging

from .celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="voice.execute_call",
    queue="voice",
    bind=True,
    max_retries=2,
    soft_time_limit=600,
    time_limit=660,
)
def execute_voice_call(self, call_record_id: str) -> dict:
    """Execute a single voice call (real or simulated).

    Args:
        call_record_id: UUID string of the CallRecord to call.

    Returns:
        Dict with call result.
    """
    from ..database import SessionLocal
    from ..services.voice import voice_service

    db = SessionLocal()
    try:
        result = _run_async(voice_service.start_call(call_record_id, db))
        logger.info("Voice call executed: call_record=%s", call_record_id)
        return result
    except Exception as exc:
        logger.exception("Voice call failed: call_record=%s", call_record_id)
        raise self.retry(exc=exc, countdown=30) from exc
    finally:
        db.close()


@celery_app.task(
    name="voice.process_completed",
    queue="voice",
    bind=True,
    max_retries=1,
    soft_time_limit=300,
    time_limit=360,
)
def process_completed_call(self, call_record_id: str) -> dict:
    """Run post-call processing: extraction, findings generation.

    Args:
        call_record_id: UUID string of the completed CallRecord.

    Returns:
        Dict with extraction_result and findings_count.
    """
    from ..database import SessionLocal
    from ..services.voice import voice_service

    db = SessionLocal()
    try:
        result = _run_async(voice_service.process_completed_call(call_record_id, db))
        logger.info(
            "Post-processing complete: call_record=%s findings=%d",
            call_record_id,
            result.get("findings_count", 0),
        )
        return result
    except Exception as exc:
        logger.exception("Post-processing failed: call_record=%s", call_record_id)
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()


@celery_app.task(
    name="voice.execute_batch",
    queue="voice",
    bind=True,
    max_retries=0,
    soft_time_limit=3600,
    time_limit=3900,
)
def execute_voice_batch(self, voice_extraction_id: str) -> dict:
    """Execute all pending calls for a VoiceExtraction sequentially.

    Calls are made one at a time with a brief delay between each to avoid
    overwhelming the target or Twilio rate limits.

    Args:
        voice_extraction_id: UUID string of the VoiceExtraction.

    Returns:
        Dict with total, completed, failed counts.
    """
    from ..database import SessionLocal
    from ..services.voice import voice_service

    db = SessionLocal()
    try:
        result = _run_async(voice_service.execute_batch(voice_extraction_id, db))
        logger.info(
            "Batch execution complete: voice_extraction=%s total=%d completed=%d",
            voice_extraction_id,
            result.get("total", 0),
            result.get("completed", 0),
        )
        return result
    except Exception:
        logger.exception("Batch execution failed: voice_extraction=%s", voice_extraction_id)
        raise
    finally:
        db.close()
