from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from ..models.call_campaign import CallCampaign
from ..models.call_log import CallLog
from . import gemini

logger = logging.getLogger(__name__)

_CLASSIFICATION_SCHEMA = """{
  "outcome": "connected | voicemail | no_answer | busy | failed | callback_scheduled",
  "person_reached": "receptionist | hiring_manager | voicemail | unknown",
  "summary": "string -- 2-3 sentence summary of the call",
  "next_steps": {
    "action": "string -- follow_up_call | send_email | schedule_interview | none",
    "notes": "string",
    "callback_date": "string ISO date or null"
  }
}"""


async def process_call_result(
    db: Session, call_log: CallLog, transcript: str
) -> None:
    """Classify and summarise a completed call using Gemini.

    Updates the call_log with the classification results.  If a callback is
    scheduled, creates a new campaign entry for the follow-up call.

    Args:
        db: Active database session.
        call_log: The CallLog row to update.
        transcript: Full transcript text of the call.
    """
    if not transcript or not transcript.strip():
        call_log.outcome = call_log.outcome or "no_answer"
        call_log.summary = "No transcript available."
        db.commit()
        return

    prompt = f"""Classify this cold-call transcript.

TRANSCRIPT:
{transcript[:4000]}

Based on the transcript, determine:
1. outcome -- what happened on the call
2. person_reached -- who actually answered
3. summary -- 2-3 sentence summary
4. next_steps -- recommended follow-up action

Return ONLY valid JSON matching the schema."""

    try:
        classification: dict[str, Any] = await gemini.generate_structured(
            prompt, schema_hint=_CLASSIFICATION_SCHEMA
        )
    except Exception:
        logger.exception("Failed to classify call %s", call_log.id)
        call_log.summary = "Classification failed -- manual review needed."
        db.commit()
        return

    call_log.outcome = classification.get("outcome", "unknown")
    call_log.person_reached = classification.get("person_reached", "unknown")
    call_log.summary = classification.get("summary", "")
    call_log.transcript = transcript
    call_log.next_steps = classification.get("next_steps")

    db.commit()

    # If a callback was scheduled, create a follow-up campaign entry
    next_steps = classification.get("next_steps") or {}
    if next_steps.get("action") == "follow_up_call":
        campaign = (
            db.query(CallCampaign)
            .filter(CallCampaign.id == call_log.campaign_id)
            .first()
        )
        if campaign and campaign.attempt_count < campaign.max_attempts:
            callback_date_str = next_steps.get("callback_date")
            scheduled_at = None
            if callback_date_str:
                try:
                    scheduled_at = datetime.fromisoformat(callback_date_str)
                except ValueError:
                    scheduled_at = datetime.utcnow() + timedelta(hours=48)
            else:
                scheduled_at = datetime.utcnow() + timedelta(hours=48)

            followup = CallCampaign(
                user_id=campaign.user_id,
                match_id=campaign.match_id,
                contact_id=campaign.contact_id,
                status="scheduled",
                scheduled_at=scheduled_at,
                priority=campaign.priority,
                max_attempts=campaign.max_attempts - campaign.attempt_count,
            )
            db.add(followup)
            db.commit()
            logger.info(
                "Follow-up campaign %s created for contact %s (user=%s)",
                followup.id,
                campaign.contact_id,
                campaign.user_id,
            )
