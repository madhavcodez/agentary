"""Orchestrator for the voice extraction system.

Provides the main entry points for creating voice extractions, planning calls,
executing calls (real or simulated), and processing completed calls.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ...core.events import Event, EventType, event_bus
from ...models.enums import FailureCategory
from ...models.voice_extraction import (
    CallDirection,
    CallRecord,
    CallStatus,
    VoiceExtraction,
    VoiceExtractionStatus,
)
from . import extraction_service, transcript_processor, voice_pipeline_adapter

logger = logging.getLogger(__name__)


def _append_call_transition(
    call_record: CallRecord,
    from_state: str,
    to_state: str,
    reason: str | None = None,
) -> None:
    """Append a state transition record to a CallRecord.

    Validates the transition using CALL_VALID_TRANSITIONS from the state machine.
    """
    from ..state_machine import InvalidTransition, call_transition

    try:
        record = call_transition(from_state, to_state, reason)
    except InvalidTransition:
        logger.warning(
            "Invalid call transition %s -> %s (reason=%s); recording anyway",
            from_state, to_state, reason,
        )
        record = {
            "from": from_state,
            "to": to_state,
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": reason,
        }
    transitions = list(call_record.state_transitions or [])
    transitions.append(record)
    call_record.state_transitions = transitions


async def create_voice_extraction(
    data: dict[str, Any],
    db: Session,
) -> VoiceExtraction:
    """Create a new VoiceExtraction campaign.

    Args:
        data: Dict with project_id, name, description, objective, persona,
              extraction_schema, targets, etc.
        db: Database session.

    Returns:
        Created VoiceExtraction.
    """
    ve = VoiceExtraction(
        id=uuid.uuid4(),
        project_id=data["project_id"],
        mission_id=data.get("mission_id"),
        name=data["name"],
        description=data.get("description"),
        objective=data.get("objective"),
        persona=data.get("persona", {}),
        extraction_schema=data.get("extraction_schema", {}),
        call_script_template=data.get("call_script_template"),
        objection_handlers=data.get("objection_handlers", []),
        max_call_duration_seconds=data.get("max_call_duration_seconds", 300),
        business_hours_only=data.get("business_hours_only", True),
        targets=data.get("targets", []),
        total_targets=len(data.get("targets", [])),
    )
    db.add(ve)
    db.flush()

    logger.info(
        "Created VoiceExtraction %s: '%s' with %d targets",
        ve.id,
        ve.name,
        ve.total_targets,
    )
    return ve


async def plan_calls(
    voice_extraction: VoiceExtraction,
    targets: list[dict[str, Any]],
    db: Session,
) -> list[CallRecord]:
    """Create planned CallRecords for a list of targets.

    Each target should have at minimum: phone_number, name.
    Optionally: context (dict of known info about the target).

    Args:
        voice_extraction: Parent VoiceExtraction.
        targets: List of target dicts [{phone_number, name, context}].
        db: Database session.

    Returns:
        List of created CallRecord objects.
    """
    records: list[CallRecord] = []

    for target in targets:
        record = CallRecord(
            id=uuid.uuid4(),
            voice_extraction_id=voice_extraction.id,
            mission_id=voice_extraction.mission_id,
            project_id=voice_extraction.project_id,
            phone_number=target.get("phone_number", ""),
            target_name=target.get("name", "Unknown"),
            target_context=target.get("context", {}),
            direction=CallDirection.outbound,
            status=CallStatus.pending,
        )
        db.add(record)
        records.append(record)

    # Update target count
    voice_extraction.total_targets = len(targets)
    voice_extraction.targets = targets
    db.add(voice_extraction)
    db.flush()

    logger.info(
        "Planned %d calls for VoiceExtraction %s",
        len(records),
        voice_extraction.id,
    )
    return records


async def start_call(
    call_record_id: uuid.UUID,
    db: Session,
) -> dict[str, Any]:
    """Initiate a call for a specific CallRecord.

    Uses Twilio if configured, otherwise falls back to simulation mode.

    Args:
        call_record_id: UUID of the CallRecord to start.
        db: Database session.

    Returns:
        Dict with call_sid and status.
    """
    call_record = (
        db.query(CallRecord)
        .filter(CallRecord.id == call_record_id)
        .first()
    )
    if not call_record:
        raise ValueError(f"CallRecord {call_record_id} not found")

    voice_extraction = (
        db.query(VoiceExtraction)
        .filter(VoiceExtraction.id == call_record.voice_extraction_id)
        .first()
    )
    if not voice_extraction:
        raise ValueError(
            f"VoiceExtraction {call_record.voice_extraction_id} not found"
        )

    # Activate the extraction if it's still in draft
    if voice_extraction.status == VoiceExtractionStatus.draft:
        voice_extraction.status = VoiceExtractionStatus.active
        db.add(voice_extraction)

    old_status = call_record.status.value if hasattr(call_record.status, 'value') else str(call_record.status)
    result = await voice_pipeline_adapter.create_outbound_call(
        call_record, voice_extraction, db
    )
    new_status = call_record.status.value if hasattr(call_record.status, 'value') else str(call_record.status)
    if old_status != new_status:
        _append_call_transition(call_record, old_status, new_status, "Call initiated")

    await event_bus.broadcast(Event(
        event_type=EventType.run_state_changed,
        data={
            "run_type": "voice",
            "run_id": str(call_record.id),
            "from_state": old_status,
            "to_state": new_status,
            "reason": "Call initiated",
        },
        project_id=str(voice_extraction.project_id) if voice_extraction.project_id else None,
        mission_id=str(voice_extraction.mission_id) if voice_extraction.mission_id else None,
    ))

    db.commit()
    return result


async def process_completed_call(
    call_record_id: uuid.UUID,
    db: Session,
    *,
    skip_completion_check: bool = False,
) -> dict[str, Any]:
    """Run post-call processing: transcript analysis, extraction, findings.

    Args:
        call_record_id: UUID of the completed CallRecord.
        db: Database session.
        skip_completion_check: When True, skip the per-call COUNT query that
            checks if all calls are done. Callers like execute_batch do a
            single aggregation after the loop instead (avoids N+1).

    Returns:
        Dict with extraction_result and findings_count.
    """
    call_record = (
        db.query(CallRecord)
        .filter(CallRecord.id == call_record_id)
        .first()
    )
    if not call_record:
        raise ValueError(f"CallRecord {call_record_id} not found")

    voice_extraction = (
        db.query(VoiceExtraction)
        .filter(VoiceExtraction.id == call_record.voice_extraction_id)
        .first()
    )
    if not voice_extraction:
        raise ValueError(
            f"VoiceExtraction {call_record.voice_extraction_id} not found"
        )

    # 1. Process transcript
    if call_record.transcript:
        analysis = transcript_processor.process_transcript(call_record.transcript)
        call_record.extraction_notes = (
            f"Talk ratio: {analysis.get('talk_ratio', {})}\n"
            f"Key moments: {len(analysis.get('key_moments', []))}\n"
            f"Word count: {analysis.get('word_count', 0)}"
        )

    # 2. Extract structured data
    extraction_result = await extraction_service.extract_from_transcript(
        call_record, voice_extraction, db
    )

    # 3. Generate findings
    findings = await extraction_service.extract_findings(
        call_record, voice_extraction, extraction_result, db
    )

    # 4. Update counters on the parent VoiceExtraction
    voice_extraction.calls_completed = (voice_extraction.calls_completed or 0) + 1
    if extraction_result.get("quality_score", 0) > 0.5:
        voice_extraction.calls_successful = (
            voice_extraction.calls_successful or 0
        ) + 1
    voice_extraction.data_points_extracted = (
        voice_extraction.data_points_extracted or 0
    ) + len(findings)

    # Check if all calls are done (skipped during batch to avoid N+1)
    if not skip_completion_check:
        total_completed = (
            db.query(CallRecord)
            .filter(
                CallRecord.voice_extraction_id == voice_extraction.id,
                CallRecord.status == CallStatus.completed,
            )
            .count()
        )
        if total_completed >= voice_extraction.total_targets:
            voice_extraction.status = VoiceExtractionStatus.completed

    db.add(voice_extraction)
    db.commit()

    # Emit signal for the intelligence pipeline
    try:
        from ...models.signal import SignalSourceType, SignalType
        from ..intelligence.signal_service import SignalService

        if call_record.project_id:
            signal_svc = SignalService(db)
            signal_svc.create_signal(
                project_id=call_record.project_id,
                user_id=getattr(voice_extraction, "user_id", None) or call_record.project_id,
                source_type=SignalSourceType.voice,
                signal_type=SignalType.data_extracted,
                title=f"Call extraction: {call_record.target_name}",
                content=call_record.transcript[:500] if call_record.transcript else None,
                structured_data=call_record.extracted_data or {},
                source_id=call_record.id,
                confidence=call_record.extraction_confidence,
            )
            db.commit()
    except Exception:
        logger.debug("Signal emission failed for call_record %s", call_record.id)

    logger.info(
        "Post-processing complete for call_record %s: "
        "%d findings, confidence=%.2f",
        call_record.id,
        len(findings),
        extraction_result.get("overall_confidence", 0),
    )

    return {
        "extraction_result": extraction_result,
        "findings_count": len(findings),
    }


async def execute_batch(
    voice_extraction_id: uuid.UUID,
    db: Session,
) -> dict[str, Any]:
    """Execute all pending calls for a VoiceExtraction sequentially.

    Args:
        voice_extraction_id: UUID of the VoiceExtraction.
        db: Database session.

    Returns:
        Dict with total, completed, failed counts and per-call results.
    """
    voice_extraction = (
        db.query(VoiceExtraction)
        .filter(VoiceExtraction.id == voice_extraction_id)
        .first()
    )
    if not voice_extraction:
        raise ValueError(f"VoiceExtraction {voice_extraction_id} not found")

    pending_records = (
        db.query(CallRecord)
        .filter(
            CallRecord.voice_extraction_id == voice_extraction_id,
            CallRecord.status == CallStatus.pending,
        )
        .all()
    )

    if not pending_records:
        return {"total": 0, "completed": 0, "failed": 0, "results": []}

    voice_extraction.status = VoiceExtractionStatus.active
    db.add(voice_extraction)
    db.commit()

    results: list[dict[str, Any]] = []
    completed = 0
    failed = 0

    for record in pending_records:
        try:
            # Start the call
            call_result = await voice_pipeline_adapter.create_outbound_call(
                record, voice_extraction, db
            )
            db.commit()

            # If simulated, process immediately
            if call_result.get("simulated"):
                post_result = await process_completed_call(record.id, db, skip_completion_check=True)
                status = "completed"
                results.append(
                    {
                        "call_record_id": str(record.id),
                        "target_name": record.target_name,
                        "status": status,
                        **post_result,
                    }
                )
                completed += 1
            else:
                # Real calls are processed via Twilio webhooks
                status = "initiated"
                results.append(
                    {
                        "call_record_id": str(record.id),
                        "target_name": record.target_name,
                        "status": status,
                        "call_sid": call_result.get("call_sid"),
                    }
                )
                completed += 1

            # Emit per-call event
            await event_bus.broadcast(Event(
                event_type=EventType.run_state_changed,
                data={
                    "run_type": "voice",
                    "call_id": str(record.id),
                    "status": status,
                },
                project_id=str(voice_extraction.project_id) if voice_extraction.project_id else None,
            ))

        except Exception as exc:
            logger.exception(
                "Failed to execute call for record %s", record.id
            )
            old_st = record.status.value if hasattr(record.status, 'value') else str(record.status)
            record.status = CallStatus.failed
            record.failure_category = FailureCategory.internal
            record.failure_message = str(exc)
            _append_call_transition(record, old_st, "failed", str(exc))
            db.add(record)
            db.commit()
            results.append(
                {
                    "call_record_id": str(record.id),
                    "target_name": record.target_name,
                    "status": "failed",
                }
            )
            failed += 1

            # Emit per-call failure event
            await event_bus.broadcast(Event(
                event_type=EventType.run_state_changed,
                data={
                    "run_type": "voice",
                    "call_id": str(record.id),
                    "status": "failed",
                },
                project_id=str(voice_extraction.project_id) if voice_extraction.project_id else None,
            ))

    # Single aggregation after batch loop (avoids N+1 per-call COUNT queries)
    total_completed = (
        db.query(CallRecord)
        .filter(
            CallRecord.voice_extraction_id == voice_extraction_id,
            CallRecord.status == CallStatus.completed,
        )
        .count()
    )
    if total_completed >= voice_extraction.total_targets:
        voice_extraction.status = VoiceExtractionStatus.completed
        db.add(voice_extraction)
        db.commit()

    return {
        "total": len(pending_records),
        "completed": completed,
        "failed": failed,
        "results": results,
    }


def get_extraction_status(
    voice_extraction_id: uuid.UUID,
    db: Session,
) -> dict[str, Any]:
    """Get real-time status of a voice extraction campaign.

    Args:
        voice_extraction_id: UUID of the VoiceExtraction.
        db: Database session.

    Returns:
        Dict with status, progress, and per-call statuses.
    """
    ve = (
        db.query(VoiceExtraction)
        .filter(VoiceExtraction.id == voice_extraction_id)
        .first()
    )
    if not ve:
        raise ValueError(f"VoiceExtraction {voice_extraction_id} not found")

    records = (
        db.query(CallRecord)
        .filter(CallRecord.voice_extraction_id == voice_extraction_id)
        .all()
    )

    status_counts: dict[str, int] = {}
    for r in records:
        s = r.status.value if hasattr(r.status, "value") else str(r.status)
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "id": str(ve.id),
        "name": ve.name,
        "status": ve.status.value if hasattr(ve.status, "value") else str(ve.status),
        "total_targets": ve.total_targets,
        "calls_completed": ve.calls_completed,
        "calls_successful": ve.calls_successful,
        "data_points_extracted": ve.data_points_extracted,
        "call_statuses": status_counts,
        "records": [
            {
                "id": str(r.id),
                "target_name": r.target_name,
                "phone_number": r.phone_number,
                "status": r.status.value if hasattr(r.status, "value") else str(r.status),
                "extracted_data": r.extracted_data,
                "extraction_confidence": r.extraction_confidence,
            }
            for r in records
        ],
    }
