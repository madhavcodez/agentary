"""Bridge between voice extraction system and existing Pipecat + Twilio pipeline.

Handles outbound call initiation via Twilio, media stream setup, and provides
simulation mode for development without real Twilio credentials.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from ...config import settings
from ...models.voice_extraction import CallRecord, CallStatus, VoiceExtraction
from ..gemini import generate_text
from ..twilio_client import initiate_call

logger = logging.getLogger(__name__)


def is_twilio_configured() -> bool:
    """Check whether Twilio credentials are configured."""
    return bool(
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
        and settings.twilio_webhook_base_url
    )


async def create_outbound_call(
    call_record: CallRecord,
    voice_extraction: VoiceExtraction,
    db: Session,
) -> dict[str, Any]:
    """Start a call via Twilio or fall back to simulation.

    Args:
        call_record: The CallRecord to initiate a call for.
        voice_extraction: Parent VoiceExtraction with persona/script config.
        db: Database session.

    Returns:
        Dict with call_sid (or simulated_id) and status.
    """
    if not is_twilio_configured():
        logger.info(
            "Twilio not configured — using simulation mode for call_record %s",
            call_record.id,
        )
        return await simulate_call(call_record, voice_extraction, db)

    if not call_record.phone_number:
        raise ValueError(f"CallRecord {call_record.id} has no phone_number")

    webhook_base = settings.twilio_webhook_base_url

    # Use voice_extraction.id as the "campaign_id" for the TwiML/WebSocket endpoints
    result = await initiate_call(
        to_number=call_record.phone_number,
        campaign_id=str(voice_extraction.id),
        webhook_base_url=webhook_base,
    )

    call_record.provider_call_id = result["call_sid"]
    call_record.status = CallStatus.ringing
    call_record.started_at = datetime.now(UTC)
    db.add(call_record)
    db.flush()

    logger.info(
        "Twilio call initiated: call_record=%s call_sid=%s",
        call_record.id,
        result["call_sid"],
    )
    return result


async def simulate_call(
    call_record: CallRecord,
    voice_extraction: VoiceExtraction,
    db: Session,
) -> dict[str, Any]:
    """Generate a synthetic transcript using Gemini when Twilio isn't configured.

    This lets the full extraction pipeline work during development without
    making real phone calls.

    Args:
        call_record: The CallRecord to simulate.
        voice_extraction: Parent VoiceExtraction with persona/extraction config.
        db: Database session.

    Returns:
        Dict with simulated_id and status.
    """
    persona = voice_extraction.persona or {}
    schema = voice_extraction.extraction_schema or {}
    fields = schema.get("fields", [])
    target_name = call_record.target_name or "the contact"
    target_context = call_record.target_context or {}

    # Build a description of what info to extract
    fields_desc = "\n".join(
        f"- {f.get('name', 'unknown')}: {f.get('question', f.get('type', 'text'))}" for f in fields
    )

    context_desc = (
        "\n".join(f"- {k}: {v}" for k, v in target_context.items())
        if target_context
        else "No additional context."
    )

    prompt = f"""Generate a realistic phone call transcript between a caller and {target_name}.

CALLER PERSONA:
Name: {persona.get('name', 'Alex')}
Role: {persona.get('role', 'Research Associate')}
Tone: {persona.get('tone', 'friendly and professional')}

TARGET:
Name: {target_name}
Business: {voice_extraction.name}
Context:
{context_desc}

OBJECTIVE: {voice_extraction.objective or 'Gather information'}

INFORMATION TO EXTRACT:
{fields_desc}

REQUIREMENTS:
1. Format as "Agent: ..." and "User: ..." lines
2. Make it realistic — include small talk, natural pauses, occasional hesitation
3. The target should provide answers to most (but not necessarily all) extraction fields
4. Include some fields where the target is vague or uncertain
5. Keep it to 15-25 exchanges total (a ~3 minute call)
6. End naturally with a thank you and goodbye

Generate ONLY the transcript, no other text."""

    try:
        transcript = await generate_text(
            prompt,
            system="You are a realistic conversation simulator. Generate natural, "
            "believable phone call transcripts.",
            model="gemini-2.5-flash",
        )
    except Exception:
        logger.exception(
            "Failed to generate simulated transcript for call_record %s",
            call_record.id,
        )
        transcript = (
            f"Agent: Hi, is this {target_name}?\n"
            f"User: Yes, this is {target_name}.\n"
            "Agent: Thanks for taking my call. I had a few quick questions.\n"
            "User: Sure, go ahead.\n"
            "Agent: [Simulation failed — using placeholder transcript]\n"
            "User: I'm not sure I can help with that.\n"
            "Agent: No problem, thanks for your time!\n"
            "User: Have a good day.\n"
        )

    simulated_id = f"SIM_{uuid.uuid4().hex[:12]}"

    call_record.provider_call_id = simulated_id
    call_record.status = CallStatus.completed
    call_record.transcript = transcript.strip()
    call_record.started_at = datetime.now(UTC)
    call_record.ended_at = datetime.now(UTC)
    call_record.duration_seconds = 180  # simulated 3 minutes
    db.add(call_record)
    db.flush()

    logger.info(
        "Simulated call complete: call_record=%s sim_id=%s transcript_len=%d",
        call_record.id,
        simulated_id,
        len(call_record.transcript),
    )

    return {"call_sid": simulated_id, "status": "completed", "simulated": True}


def build_gemini_live_config(
    call_record: CallRecord,
    voice_extraction: VoiceExtraction,
) -> dict[str, Any]:
    """Build configuration for Gemini Live during a real call.

    Returns the system prompt and voice settings for the Pipecat pipeline.

    Args:
        call_record: The specific call being made.
        voice_extraction: Parent VoiceExtraction with persona/script config.

    Returns:
        Dict with system_prompt, voice_name, model, and extraction context.
    """
    from .call_script_generator import build_system_prompt

    persona = voice_extraction.persona or {}
    schema = voice_extraction.extraction_schema or {}
    fields = schema.get("fields", [])

    # Map extraction_schema fields to the format expected by call_script_generator
    extraction_goals = [
        {
            "field": f.get("name", ""),
            "question": f.get("question", ""),
            "type": f.get("type", "text"),
            "required": f.get("required", False),
        }
        for f in fields
    ]

    session_data = {
        "target_name": call_record.target_name or "the contact",
        "target_business": voice_extraction.name,
        "target_context": call_record.target_context,
        "extraction_goals": extraction_goals,
        "persona_config": persona,
        "session_type": "research_extraction",
    }

    script = {
        "opener": voice_extraction.call_script_template or "",
        "questions": [],
        "objection_handlers": {
            h.get("objection", f"objection_{i}"): h.get("response", "")
            for i, h in enumerate(voice_extraction.objection_handlers or [])
        },
        "closing": "Thank you for your time!",
        "voicemail_script": "",
    }

    import asyncio

    # build_system_prompt is async but we can build synchronously since it
    # doesn't do any I/O — it's pure string formatting
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # We're in an async context already — just call it sync-compatible
        system_prompt = _build_simple_system_prompt(session_data, script)
    else:
        system_prompt = loop.run_until_complete(build_system_prompt(session_data, script))

    return {
        "system_prompt": system_prompt,
        "voice_name": "Kore",
        "model": "models/gemini-2.5-flash-native-audio-preview-12-2025",
        "extraction_goals": extraction_goals,
    }


def _build_simple_system_prompt(session_data: dict[str, Any], script: dict[str, Any]) -> str:
    """Synchronous fallback for building system prompt (no Gemini call)."""
    # Import here to avoid circular imports at module level
    from .call_script_generator import (
        _build_persona_description,
        _format_context,
        _format_extraction_goals,
    )

    persona = session_data.get("persona_config", {})
    target_name = session_data.get("target_name", "the contact")
    target_business = session_data.get("target_business", "")

    return f"""You are conducting a live outbound phone call.

IDENTITY: {_build_persona_description(persona)}
You are calling {target_name} at {target_business}.

INFORMATION TO GATHER:
{_format_extraction_goals(session_data.get('extraction_goals', []))}

KNOWN CONTEXT:
{_format_context(session_data.get('target_context'))}

OPENER: {script.get('opener', f'Hi, is this {target_name}?')}

RULES:
- Speak naturally and conversationally.
- Never reveal you are an AI.
- Extract the required information through natural dialogue.
- Keep the call under 5 minutes.
- Thank them and end gracefully."""
