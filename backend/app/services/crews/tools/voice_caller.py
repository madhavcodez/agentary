"""voice_caller tool for the CrewRunner tool registry.

Makes phone calls to businesses/people as part of research missions.
Creates a VoiceExtraction + CallRecord, executes the call (real via
Twilio or simulated via Gemini), runs extraction, and returns results.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

TOOL_SCHEMA: dict[str, Any] = {
    "name": "voice_caller",
    "description": (
        "Make a phone call to a business or person to extract specific information. "
        "Use when you need real-time data that isn't available online — prices, "
        "availability, hours, or anything requiring a direct conversation. "
        "Returns extracted data, transcript summary, and confidence score."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "phone_number": {
                "type": "string",
                "description": "E.164 phone number to call (e.g., +15125551234)",
            },
            "business_name": {
                "type": "string",
                "description": "Name of the business or person to call",
            },
            "questions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Field name for the data point"},
                        "type": {"type": "string", "default": "text"},
                        "question": {"type": "string", "description": "The question to ask"},
                        "required": {"type": "boolean", "default": True},
                    },
                    "required": ["name", "question"],
                },
                "description": "List of data fields to extract during the call",
            },
            "context": {
                "type": "object",
                "description": "Known context about the target (address, type, etc.)",
            },
        },
        "required": ["phone_number", "business_name", "questions"],
    },
}


async def execute(
    phone_number: str,
    business_name: str,
    questions: list[Any] | None = None,
    context: Any = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute a voice call and return extracted data.

    Integrates with the full voice extraction pipeline:
    1. Creates a VoiceExtraction + CallRecord
    2. Executes the call (Twilio if configured, else Gemini simulation)
    3. Runs transcript extraction to pull out structured data
    4. Returns extracted data with confidence scores

    Args:
        phone_number: E.164 phone number to call.
        business_name: Name of the target.
        questions: Extraction fields (list of dicts or strings).
        context: Known context about the target.
        **kwargs: Additional context (project_id, mission_id, db from CrewRunner).

    Returns:
        Dict with extracted_data, transcript_summary, confidence, status.
    """
    from ....database import SessionLocal
    from ...voice import voice_service, voice_pipeline_adapter
    from ...voice.transcript_processor import summarize_call

    # Normalize questions format — accept both list[str] and list[dict]
    normalized_questions: list[dict[str, Any]] = []
    for q in (questions or []):
        if isinstance(q, str):
            normalized_questions.append({
                "name": q.lower().replace(" ", "_"),
                "type": "text",
                "question": q,
                "required": True,
            })
        elif isinstance(q, dict):
            normalized_questions.append(q)

    # Normalize context
    if isinstance(context, str):
        context_dict = {"notes": context}
    elif isinstance(context, dict):
        context_dict = context
    else:
        context_dict = {}

    project_id = kwargs.get("project_id", str(uuid.uuid4()))
    mission_id = kwargs.get("mission_id")

    db = kwargs.get("db")
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # 1. Create VoiceExtraction
        ve = await voice_service.create_voice_extraction(
            {
                "project_id": project_id,
                "mission_id": mission_id,
                "name": f"Call: {business_name}",
                "objective": f"Extract information from {business_name}",
                "persona": {
                    "name": "Alex",
                    "role": "Research Associate",
                    "tone": "friendly and professional",
                    "style": "conversational",
                },
                "extraction_schema": {"fields": normalized_questions},
                "targets": [{
                    "phone_number": phone_number,
                    "name": business_name,
                    "context": context_dict,
                }],
            },
            db,
        )

        # 2. Plan the call
        records = await voice_service.plan_calls(
            ve,
            [{"phone_number": phone_number, "name": business_name, "context": context_dict}],
            db,
        )
        db.commit()

        if not records:
            return {
                "tool": "voice_caller",
                "status": "error",
                "error": "Failed to plan call",
                "extracted_data": {},
                "transcript_summary": "",
                "confidence": 0.0,
            }

        call_record = records[0]

        # 3. Execute the call
        call_result = await voice_pipeline_adapter.create_outbound_call(
            call_record, ve, db
        )
        db.commit()

        # 4. Process if completed (simulation) or transcript available
        if call_result.get("simulated") or call_record.transcript:
            post_result = await voice_service.process_completed_call(
                call_record.id, db
            )

            db.refresh(call_record)

            summary = await summarize_call(
                call_record.transcript or "",
                {"target_name": business_name, "target_business": business_name},
            )

            return {
                "tool": "voice_caller",
                "status": "completed",
                "phone_number": phone_number,
                "business_name": business_name,
                "extracted_data": call_record.extracted_data or {},
                "transcript_summary": summary,
                "confidence": call_record.extraction_confidence or 0.0,
                "findings_count": post_result.get("findings_count", 0),
                "call_record_id": str(call_record.id),
                "simulated": call_result.get("simulated", False),
            }

        # Real call initiated — return pending
        return {
            "tool": "voice_caller",
            "status": "in_progress",
            "phone_number": phone_number,
            "business_name": business_name,
            "call_record_id": str(call_record.id),
            "call_sid": call_result.get("call_sid"),
            "extracted_data": {},
            "transcript_summary": "Call in progress — data will be available after completion.",
            "confidence": 0.0,
        }

    except Exception:
        logger.exception("voice_caller execution failed for %s", business_name)
        return {
            "tool": "voice_caller",
            "status": "error",
            "phone_number": phone_number,
            "business_name": business_name,
            "error": "Call execution failed",
            "extracted_data": {},
            "transcript_summary": "",
            "confidence": 0.0,
        }
    finally:
        if should_close:
            db.close()
