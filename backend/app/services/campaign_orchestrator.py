from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..config import settings
from ..models.call_campaign import CallCampaign
from ..models.call_log import CallLog
from ..voice.policy.engine import PolicyEngine
from ..voice.policy.rules import OUTBOUND_LIMITS
from . import twilio_client

logger = logging.getLogger(__name__)

_policy_engine = PolicyEngine()


async def process_call_queue(db: Session) -> int:
    """Process the outbound call queue.

    Finds campaigns that are ready to dial (status=scheduled, scheduled_at <=
    now) and initiates calls via Twilio, subject to policy checks.

    Args:
        db: Active database session.

    Returns:
        Number of calls successfully initiated.
    """
    now = datetime.utcnow()

    # Check daily call limit
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = (
        db.query(CallLog)
        .filter(CallLog.created_at >= today_start)
        .count()
    )
    remaining_daily = OUTBOUND_LIMITS["max_daily_calls"] - daily_count
    if remaining_daily <= 0:
        logger.warning("Daily outbound call limit reached (%d)", OUTBOUND_LIMITS["max_daily_calls"])
        return 0

    # Pre-call policy check (business hours, etc.)
    policy_result = _policy_engine.evaluate_pre_call({})
    if not policy_result["allowed"]:
        logger.info(
            "Pre-call policy blocked queue processing: %s",
            policy_result["violations"],
        )
        return 0

    # Fetch ready campaigns
    campaigns = (
        db.query(CallCampaign)
        .filter(
            CallCampaign.status.in_(["scheduled", "pending"]),
            (CallCampaign.scheduled_at <= now) | (CallCampaign.scheduled_at.is_(None)),
        )
        .order_by(CallCampaign.priority.desc(), CallCampaign.created_at.asc())
        .limit(remaining_daily)
        .all()
    )

    initiated = 0
    webhook_base = settings.twilio_webhook_base_url
    if not webhook_base:
        logger.error("TWILIO_WEBHOOK_BASE_URL not configured -- cannot place calls")
        return 0

    for campaign in campaigns:
        # Per-contact cooldown check
        cooldown_hours = OUTBOUND_LIMITS["min_company_cooldown_hours"]
        cooldown_cutoff = now - timedelta(hours=cooldown_hours)
        recent_to_contact = (
            db.query(CallLog)
            .join(CallCampaign, CallLog.campaign_id == CallCampaign.id)
            .filter(
                CallCampaign.contact_id == campaign.contact_id,
                CallLog.created_at >= cooldown_cutoff,
            )
            .count()
        )
        if recent_to_contact > 0:
            logger.debug(
                "Skipping campaign %s -- contact %s called within %dh cooldown",
                campaign.id,
                campaign.contact_id,
                cooldown_hours,
            )
            continue

        # Max attempts check
        if campaign.attempt_count >= campaign.max_attempts:
            campaign.status = "failed"
            db.commit()
            logger.info("Campaign %s exhausted max attempts", campaign.id)
            continue

        # Retry logic
        last_log = (
            db.query(CallLog)
            .filter(CallLog.campaign_id == campaign.id)
            .order_by(CallLog.created_at.desc())
            .first()
        )
        if not _should_retry(campaign, last_log):
            continue

        try:
            phone = campaign.contact.phone
            result = await twilio_client.initiate_call(
                to_number=phone,
                campaign_id=str(campaign.id),
                webhook_base_url=webhook_base,
            )
            call_sid = result["call_sid"]

            # Create a call log entry with user_id from campaign
            log = CallLog(
                user_id=campaign.user_id,
                campaign_id=campaign.id,
                twilio_call_sid=call_sid,
                started_at=now,
            )
            db.add(log)

            campaign.status = "in_progress"
            campaign.attempt_count = campaign.attempt_count + 1
            db.commit()
            initiated += 1
            logger.info(
                "Initiated call for campaign %s -> %s (SID: %s)",
                campaign.id,
                phone,
                call_sid,
            )
        except Exception:
            logger.exception("Failed to initiate call for campaign %s", campaign.id)
            campaign.status = "failed"
            db.commit()

    return initiated


def _should_retry(campaign: CallCampaign, last_log: CallLog | None) -> bool:
    """Determine whether a campaign should be retried.

    Uses exponential backoff based on attempt count: wait 1h, 4h, 12h, etc.

    Args:
        campaign: The campaign in question.
        last_log: The most recent call log for this campaign, or None.

    Returns:
        True if the campaign should be retried now.
    """
    if last_log is None:
        return True

    # If last call was successful (connected), do not retry
    if last_log.outcome == "connected":
        return False

    # Exponential backoff: 1h * 2^(attempt-1)
    backoff_hours = min(1 * (2 ** (campaign.attempt_count - 1)), 48)
    if last_log.created_at:
        next_retry = last_log.created_at + timedelta(hours=backoff_hours)
        if datetime.utcnow() < next_retry:
            logger.debug(
                "Campaign %s in backoff until %s",
                campaign.id,
                next_retry.isoformat(),
            )
            return False

    return True
