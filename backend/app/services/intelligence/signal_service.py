"""Signal ingestion, deduplication, and routing."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ...core.events import Event, EventType, event_bus
from ...models.signal import Signal, SignalSourceType, SignalType

logger = logging.getLogger(__name__)


class SignalService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_signal(
        self,
        project_id: UUID,
        user_id: UUID,
        source_type: SignalSourceType,
        signal_type: SignalType,
        title: str,
        content: str | None = None,
        structured_data: dict | None = None,
        source_id: UUID | None = None,
        entity_id: UUID | None = None,
        confidence: float | None = None,
    ) -> Signal:
        """Create a signal with content-hash deduplication."""
        hash_input = f"{project_id}:{source_type.value}:{title}:{content or ''}"
        content_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:64]

        # Check for duplicate within 1 hour
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        existing = (
            self.db.query(Signal)
            .filter(
                Signal.content_hash == content_hash,
                Signal.created_at >= cutoff,
            )
            .first()
        )
        if existing:
            logger.debug("Duplicate signal detected, returning existing id=%s", existing.id)
            return existing

        signal = Signal(
            project_id=project_id,
            user_id=user_id,
            source_type=source_type,
            signal_type=signal_type,
            title=title,
            content=content,
            structured_data=structured_data or {},
            source_id=source_id,
            entity_id=entity_id,
            confidence=confidence,
            content_hash=content_hash,
        )
        self.db.add(signal)
        self.db.flush()

        # Dispatch async processing via Celery
        try:
            from ...tasks.signal_tasks import process_signal
            process_signal.delay(str(signal.id))
        except Exception:
            pass  # Celery may not be running in dev

        # Emit WebSocket event
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(event_bus.broadcast(Event(
                    event_type=EventType.signal_created,
                    data={
                        "signal_id": str(signal.id),
                        "title": signal.title,
                        "signal_type": signal.signal_type.value,
                    },
                    project_id=signal.project_id,
                )))
        except Exception:
            pass

        return signal

    def list_signals(
        self,
        project_id: UUID,
        source_type: str | None = None,
        signal_type: str | None = None,
        entity_id: UUID | None = None,
        is_processed: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Signal]:
        """List signals with optional filters."""
        q = self.db.query(Signal).filter(Signal.project_id == project_id)
        if source_type:
            q = q.filter(Signal.source_type == source_type)
        if signal_type:
            q = q.filter(Signal.signal_type == signal_type)
        if entity_id:
            q = q.filter(Signal.entity_id == entity_id)
        if is_processed is not None:
            q = q.filter(Signal.is_processed == is_processed)
        return q.order_by(Signal.created_at.desc()).offset(offset).limit(limit).all()

    def get_signal(self, signal_id: UUID) -> Signal | None:
        """Get a single signal by ID."""
        return self.db.query(Signal).filter(Signal.id == signal_id).first()

    def mark_processed(self, signal_id: UUID) -> None:
        """Mark a signal as processed."""
        signal = self.db.query(Signal).filter_by(id=signal_id).first()
        if signal:
            signal.is_processed = True
            self.db.flush()
