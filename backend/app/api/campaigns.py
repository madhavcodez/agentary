from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db
from ..models.call_campaign import CallCampaign
from ..models.call_log import CallLog
from ..models.contact import Contact
from ..models.match import Match
from ..schemas.campaign import (
    CallLogResponse,
    CampaignCreate,
    CampaignList,
    CampaignResponse,
)
from ..services import call_script_gen, twilio_client

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("", response_model=CampaignList)
def list_campaigns(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """List campaigns with optional status filter and pagination."""
    query = db.query(CallCampaign)

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
def create_campaign(body: CampaignCreate, db: Session = Depends(get_db)):
    """Create a new call campaign from a match and contact."""
    # Validate match exists
    match = db.query(Match).filter(Match.id == body.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Validate contact exists
    contact = db.query(Contact).filter(Contact.id == body.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    campaign = CallCampaign(
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
def get_campaign(campaign_id: UUID, db: Session = Depends(get_db)):
    """Get a single campaign by ID."""
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/{campaign_id}/call-now", response_model=CampaignResponse)
async def call_now(campaign_id: UUID, db: Session = Depends(get_db)):
    """Trigger an immediate outbound call for this campaign.

    Generates a script if missing, then initiates the Twilio call.
    """
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id)
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
    contact = db.query(Contact).filter(Contact.id == campaign.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    result = await twilio_client.initiate_call(
        to_number=contact.phone,
        campaign_id=str(campaign.id),
        webhook_base_url=webhook_base,
    )

    # Create call log entry
    log = CallLog(
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
async def generate_script(campaign_id: UUID, db: Session = Depends(get_db)):
    """Generate (or regenerate) the call script for a campaign."""
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id)
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
def get_campaign_logs(campaign_id: UUID, db: Session = Depends(get_db)):
    """Get all call logs for a campaign."""
    campaign = (
        db.query(CallCampaign)
        .filter(CallCampaign.id == campaign_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    logs = (
        db.query(CallLog)
        .filter(CallLog.campaign_id == campaign_id)
        .order_by(CallLog.created_at.desc())
        .all()
    )
    return logs
