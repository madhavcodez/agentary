"""Resend webhook handler for email event tracking.

Receives webhook events from Resend (delivered, opened, clicked,
bounced, complained) and stores them for analytics. Automatically
manages the suppression list for bounces and complaints.

No auth required — Resend calls this endpoint directly.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

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
    """Handle Resend webhook events. No auth required — Resend calls this."""
    body = await request.json()
    event_type = body.get("type", "")
    data = body.get("data", {})

    resend_email_id = data.get("email_id", "")

    # Store event
    event = EmailEvent(
        resend_email_id=resend_email_id,
        event_type=event_type,
        payload=data,
    )

    # Try to link to campaign via resend_email_id
    if resend_email_id:
        campaign = (
            db.query(CallCampaign)
            .filter(CallCampaign.resend_email_id == resend_email_id)
            .first()
        )
        if campaign:
            event.campaign_id = campaign.id

    db.add(event)

    # Handle side effects for bounces and complaints
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
        event_type, resend_email_id,
    )
    return {"status": "ok"}


def _add_suppression(db: Session, email: str, reason: str) -> None:
    """Add an email to the suppression list (upsert)."""
    existing = (
        db.query(EmailSuppression)
        .filter(EmailSuppression.email == email)
        .first()
    )
    if existing:
        existing.reason = reason
    else:
        db.add(EmailSuppression(email=email, reason=reason))
