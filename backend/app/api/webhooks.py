"""Resend webhook handler for email event tracking.

Receives webhook events from Resend (delivered, opened, clicked, bounced,
complained) and stores them for analytics. Manages the suppression list for
bounces and complaints.

Inbound requests are authenticated via Svix-style HMAC-SHA256 over
``{webhook_id}.{timestamp}.{body}`` — see ``core.webhook_security``. Without
this, anyone could fabricate suppression events for legitimate addresses or
forge ``EmailEvent`` rows.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..core.webhook_security import verify_resend_signature
from ..deps import get_db
from ..models.call_campaign import CallCampaign
from ..models.email_event import EmailEvent
from ..models.email_suppression import EmailSuppression

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/resend")
async def resend_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Handle Resend webhook events. Authenticated via Svix HMAC."""
    # Read the raw body *before* parsing JSON — signature is over the raw bytes.
    body_bytes = await request.body()
    verify_resend_signature(body_bytes, dict(request.headers))

    try:
        body = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON body",
        ) from exc

    event_type = body.get("type", "")
    data = body.get("data", {})
    resend_email_id = data.get("email_id", "")

    # Link to campaign to derive user_id for tenant-scoped storage.
    campaign = None
    if resend_email_id:
        campaign = (
            db.query(CallCampaign).filter(CallCampaign.resend_email_id == resend_email_id).first()
        )

    if campaign:
        event = EmailEvent(
            user_id=campaign.user_id,
            campaign_id=campaign.id,
            resend_email_id=resend_email_id,
            event_type=event_type,
            payload=data,
        )
        db.add(event)

    if event_type == "email.bounced":
        email_addr = data.get("to", [None])[0]
        if email_addr:
            _add_suppression(db, email_addr.lower(), "bounced")

    elif event_type == "email.complained":
        email_addr = data.get("to", [None])[0]
        if email_addr:
            _add_suppression(db, email_addr.lower(), "complained")

    db.commit()

    logger.info(
        "Processed Resend webhook: type=%s email_id=%s",
        event_type,
        resend_email_id,
    )
    return {"status": "ok"}


def _add_suppression(db: Session, email: str, reason: str) -> None:
    """Add an email to the suppression list (upsert)."""
    existing = db.query(EmailSuppression).filter(EmailSuppression.email == email).first()
    if existing:
        existing.reason = reason
    else:
        db.add(EmailSuppression(email=email, reason=reason))
