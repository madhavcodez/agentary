"""Twilio webhook handlers for voice extraction call status updates.

All three endpoints validate ``X-Twilio-Signature`` via
``core.webhook_security.verify_twilio_signature``. Requests without a valid
signature are rejected with 403 before any DB access. The parsed form body
is returned by the verifier so we don't pay the cost of parsing twice.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Mapping

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..core.webhook_security import verify_twilio_signature
from ..deps import get_db
from ..models.voice_extraction import CallRecord, CallStatus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["voice-webhooks"])


def _lookup_call_record(db: Session, call_sid: str) -> CallRecord | None:
    return (
        db.query(CallRecord)
        .filter(CallRecord.provider_call_id == call_sid)
        .first()
    )


@router.post("/webhooks/twilio/voice-status")
async def twilio_voice_status(
    request: Request,
    db: Session = Depends(get_db),
    form: Mapping[str, str] = Depends(verify_twilio_signature),
) -> dict[str, str]:
    """Handle Twilio status-change webhooks for voice extraction calls."""
    call_status = form.get("CallStatus", "")
    call_sid = form.get("CallSid", "")
    call_duration = form.get("CallDuration")

    logger.info(
        "Voice status webhook: status=%s sid=%s duration=%s",
        call_status,
        call_sid,
        call_duration,
    )

    if not call_sid:
        return {"status": "ignored", "reason": "no call_sid"}

    record = _lookup_call_record(db, call_sid)
    if not record:
        logger.warning("No CallRecord found for call_sid=%s", call_sid)
        return {"status": "ignored", "reason": "unknown call_sid"}

    status_map = {
        "initiated": CallStatus.pending,
        "ringing": CallStatus.ringing,
        "in-progress": CallStatus.connected,
        "completed": CallStatus.completed,
        "busy": CallStatus.failed,
        "no-answer": CallStatus.no_answer,
        "failed": CallStatus.failed,
        "canceled": CallStatus.failed,
    }
    new_status = status_map.get(call_status)
    if new_status:
        record.status = new_status

    if call_status == "in-progress":
        record.started_at = record.started_at or datetime.now(timezone.utc)

    terminal_statuses = ("completed", "busy", "no-answer", "failed", "canceled")
    if call_status in terminal_statuses:
        record.ended_at = datetime.now(timezone.utc)
        if call_duration:
            try:
                record.duration_seconds = int(call_duration)
            except ValueError:
                logger.warning("Non-integer CallDuration=%r ignored", call_duration)

        if call_status == "completed" and record.transcript:
            from ..services.voice import voice_service

            try:
                await voice_service.process_completed_call(record.id, db)
            except Exception:
                logger.exception(
                    "Post-processing failed for call_record %s", record.id
                )

    db.add(record)
    db.commit()
    return {"status": "ok"}


@router.post("/webhooks/twilio/voice-recording")
async def twilio_voice_recording(
    request: Request,
    db: Session = Depends(get_db),
    form: Mapping[str, str] = Depends(verify_twilio_signature),
) -> dict[str, str]:
    """Handle Twilio recording-available webhooks."""
    call_sid = form.get("CallSid", "")
    recording_url = form.get("RecordingUrl", "")

    logger.info(
        "Voice recording webhook: sid=%s url=%s",
        call_sid,
        recording_url,
    )

    if not call_sid or not recording_url:
        return {"status": "ignored"}

    record = _lookup_call_record(db, call_sid)
    if not record:
        return {"status": "ignored", "reason": "unknown call_sid"}

    record.recording_url = recording_url
    db.add(record)
    db.commit()
    return {"status": "ok"}


@router.post("/webhooks/twilio/voice-transcription")
async def twilio_voice_transcription(
    request: Request,
    db: Session = Depends(get_db),
    form: Mapping[str, str] = Depends(verify_twilio_signature),
) -> dict[str, str]:
    """Handle Twilio transcription-ready webhooks."""
    call_sid = form.get("CallSid", "")
    transcription_text = form.get("TranscriptionText", "")

    logger.info(
        "Voice transcription webhook: sid=%s text_len=%d",
        call_sid,
        len(transcription_text),
    )

    if not call_sid or not transcription_text:
        return {"status": "ignored"}

    record = _lookup_call_record(db, call_sid)
    if not record:
        return {"status": "ignored", "reason": "unknown call_sid"}

    record.transcript = transcription_text
    db.add(record)
    db.commit()

    from ..services.voice import voice_service

    try:
        await voice_service.process_completed_call(record.id, db)
    except Exception:
        logger.exception(
            "Post-processing failed for call_record %s", record.id
        )

    return {"status": "ok"}
