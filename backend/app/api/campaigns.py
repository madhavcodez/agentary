from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_current_user, get_db
from ..models.call_campaign import CallCampaign
from ..models.call_log import CallLog
from ..models.contact import Contact
from ..models.match import Match
from ..models.user import User
from ..schemas.campaign import (
    CallLogResponse,
    CampaignCreate,
    CampaignList,
    CampaignResponse,
)
from ..models.email_suppression import EmailSuppression
from ..services import call_script_gen, twilio_client
from ..services.email_sender import send_email
from ..services.outreach_gen import generate_outreach_package

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=CampaignList)
def list_campaigns(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List campaigns with optional status filter and pagination."""
    query = db.query(CallCampaign).filter(CallCampaign.user_id == user.id)

    if status:
        query = query.filter(CallCampaign.status == status)

    total = query.count()
    items = (
        query.order_by(CallCampaign.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return CampaignList(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=CampaignResponse, status_code=201)
def create_campaign(
    body: CampaignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new call campaign from a match and contact."""
    # Validate match exists AND belongs to user
    match = (
        db.query(Match)
        .filter(Match.id == body.match_id, Match.user_id == user.id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Validate contact exists AND belongs to user
    contact = (
        db.query(Contact)
        .filter(Contact.id == body.contact_id, Contact.user_id == user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    campaign = CallCampaign(
        user_id=user.id,
        match_id=body.match_id,
        contact_id=body.contact_id,
        scheduled_at=body.scheduled_at,
        priority=body.priority,
        max_attempts=body.max_attempts,
        status="scheduled" if body.scheduled_at else "pending",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get a single campaign by ID."""
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id, CallCampaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/{campaign_id}/call-now", response_model=CampaignResponse)
async def call_now(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Trigger an immediate outbound call for this campaign.

    Generates a script if missing, then initiates the Twilio call.
    """
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id, CallCampaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == "in_progress":
        raise HTTPException(status_code=409, detail="Call already in progress")

    webhook_base = settings.twilio_webhook_base_url
    if not webhook_base:
        raise HTTPException(
            status_code=503,
            detail="TWILIO_WEBHOOK_BASE_URL not configured",
        )

    # Generate script if not yet present
    if not campaign.script_json:
        script = await call_script_gen.generate_call_script(db, campaign)
        campaign.script_json = script
        db.commit()

    # Initiate the call
    contact = (
        db.query(Contact)
        .filter(Contact.id == campaign.contact_id, Contact.user_id == user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    result = await twilio_client.initiate_call(
        to_number=contact.phone,
        campaign_id=str(campaign.id),
        webhook_base_url=webhook_base,
    )

    # Create call log entry
    log = CallLog(
        user_id=user.id,
        campaign_id=campaign.id,
        twilio_call_sid=result["call_sid"],
        started_at=datetime.utcnow(),
    )
    db.add(log)

    campaign.status = "in_progress"
    campaign.attempt_count = campaign.attempt_count + 1
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/generate-script", response_model=CampaignResponse)
async def generate_script(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate (or regenerate) the call script for a campaign."""
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id, CallCampaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    script = await call_script_gen.generate_call_script(db, campaign)
    campaign.script_json = script
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/{campaign_id}/logs", response_model=list[CallLogResponse])
def get_campaign_logs(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get all call logs for a campaign."""
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id, CallCampaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    logs = (
        db.query(CallLog)
        .filter(CallLog.campaign_id == campaign_id, CallLog.user_id == user.id)
        .order_by(CallLog.created_at.desc())
        .all()
    )
    return logs


@router.post("/{campaign_id}/outreach-package", response_model=CampaignResponse)
async def create_outreach_package(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a full outreach package (email, LinkedIn, call script) for a campaign.

    Wraps outreach_gen.generate_outreach_package() and saves all
    generated content (email subject/draft, LinkedIn message, call
    script, and suggested sequence) to the campaign record.
    """
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id, CallCampaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    package = await generate_outreach_package(db, campaign, user_id=user.id)

    campaign.email_subject = package.get("email_subject")
    campaign.email_draft = package.get("email_draft")
    campaign.linkedin_msg = package.get("linkedin_message")
    campaign.script_json = package.get("call_script")
    campaign.outreach_sequence = ",".join(package.get("suggested_sequence", []))

    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/send-email", response_model=CampaignResponse)
async def send_campaign_email(
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send the email draft for a campaign via Resend.

    Checks suppression list, sends the email, stores the Resend
    email ID for webhook tracking, and sets email_sent_at.
    """
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id, CallCampaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if not campaign.email_draft or not campaign.email_subject:
        raise HTTPException(
            status_code=400,
            detail="No email draft. Generate an outreach package first.",
        )

    if campaign.email_sent_at:
        raise HTTPException(status_code=409, detail="Email already sent for this campaign")

    # Resolve contact email
    contact = (
        db.query(Contact)
        .filter(Contact.id == campaign.contact_id, Contact.user_id == user.id)
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if not contact.email:
        raise HTTPException(status_code=400, detail="Contact has no email address")

    # Check suppression list
    suppressed = (
        db.query(EmailSuppression)
        .filter(EmailSuppression.email == contact.email.lower())
        .first()
    )
    if suppressed:
        raise HTTPException(
            status_code=422,
            detail=f"Email suppressed: {suppressed.reason}",
        )

    # Send via Resend
    try:
        result = await send_email(
            to=contact.email,
            subject=campaign.email_subject,
            body=campaign.email_draft,
        )
    except Exception as e:
        logger.error("Failed to send email for campaign %s: %s", campaign_id, e)
        raise HTTPException(status_code=502, detail=f"Email send failed: {e}")

    # Store Resend email ID and mark as sent
    campaign.resend_email_id = result.get("id")
    campaign.email_sent_at = datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    return campaign
