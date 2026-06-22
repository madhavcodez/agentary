"""Process signals into observations and trigger insight generation."""
from __future__ import annotations

import asyncio
import logging

from ..celery_app import celery_app
from ..database import SessionLocal

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine in a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, soft_time_limit=300)
def process_signal(self, signal_id: str):
    """Process a signal: extract observations from structured data and text content."""
    db = SessionLocal()
    try:
        from ..models.signal import Signal
        from ..services.intelligence.observation_service import ObservationService
        from ..services.intelligence.signal_service import SignalService

        signal = db.query(Signal).filter_by(id=signal_id).first()
        if not signal or signal.is_processed:
            return {"status": "skipped"}

        obs_svc = ObservationService(db)

        # If signal has structured_data, create observations directly
        if signal.structured_data:
            for key, value in signal.structured_data.items():
                if isinstance(value, (str, int, float, bool)):
                    obs_svc.create_observation(
                        project_id=signal.project_id,
                        signal_id=signal.id,
                        observation_type="fact",
                        subject=key,
                        content=str(value),
                        structured_value={key: value},
                        source_type=signal.source_type.value,
                        entity_id=signal.entity_id,
                        confidence=signal.confidence,
                    )

        # If signal has text content, use Gemini to extract observations
        if signal.content and len(signal.content) > 50:
            try:
                from ..services.gemini import generate_structured

                schema_hint = (
                    '{"type": "array", "items": {"type": "object", "properties": '
                    '{"subject": {"type": "string"}, "content": {"type": "string"}, '
                    '"observation_type": {"type": "string", "enum": '
                    '["fact", "measurement", "quote", "classification", "comparison", "temporal_change"]}, '
                    '"confidence": {"type": "number"}}}}'
                )
                prompt = (
                    "Extract structured observations from this text. "
                    "Return a JSON array of objects, each with:\n"
                    "- subject: what this observation is about (string)\n"
                    "- content: the observation detail (string)\n"
                    "- observation_type: one of fact, measurement, quote, "
                    "classification, comparison, temporal_change\n"
                    "- confidence: 0.0-1.0\n\n"
                    f"Text: {signal.content[:3000]}"
                )
                extracted = _run_async(generate_structured(prompt, schema_hint))
                if isinstance(extracted, list):
                    for obs_data in extracted[:20]:
                        obs_svc.create_observation(
                            project_id=signal.project_id,
                            signal_id=signal.id,
                            observation_type=obs_data.get("observation_type", "fact"),
                            subject=obs_data.get("subject", "Unknown"),
                            content=obs_data.get("content", ""),
                            entity_id=signal.entity_id,
                            confidence=obs_data.get("confidence"),
                        )
            except Exception as e:
                logger.warning("Gemini extraction failed for signal %s: %s", signal_id, e)

        # Mark signal as processed
        signal_svc = SignalService(db)
        signal_svc.mark_processed(signal.id)
        db.commit()

        return {"status": "processed", "signal_id": signal_id}
    except Exception as e:
        db.rollback()
        logger.error("Failed to process signal %s: %s", signal_id, e)
        raise self.retry(exc=e, countdown=30) from e
    finally:
        db.close()
