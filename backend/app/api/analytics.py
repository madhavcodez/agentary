"""Analytics endpoints — funnel, channel performance, timeline, score distribution."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.call_campaign import CallCampaign
from ..models.call_log import CallLog
from ..models.email_event import EmailEvent
from ..models.match import Match
from ..models.user import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/funnel")
def get_funnel(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Pipeline funnel counts — how many matches reached each stage."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    rows = (
        db.query(Match.pipeline_stage, func.count(Match.id))
        .filter(Match.user_id == user.id, Match.created_at >= cutoff)
        .group_by(Match.pipeline_stage)
        .all()
    )
    counts = dict(rows)

    ordered_stages = [
        "lead", "contacted", "aware", "engaged",
        "meeting", "closed_won",
    ]

    funnel = []
    for stage in ordered_stages:
        funnel.append({"stage": stage, "count": counts.get(stage, 0)})

    # Compute conversion rates between adjacent stages
    for i in range(1, len(funnel)):
        prev_count = funnel[i - 1]["count"]
        curr_count = funnel[i]["count"]
        funnel[i]["conversion_rate"] = (
            round(curr_count / prev_count * 100, 1) if prev_count > 0 else 0.0
        )
    if funnel:
        funnel[0]["conversion_rate"] = 100.0

    total_matches = sum(counts.get(s, 0) for s in ordered_stages)

    return {
        "days": days,
        "total_matches": total_matches,
        "stages": funnel,
        "closed_lost": counts.get("closed_lost", 0),
        "paused": counts.get("paused", 0),
    }


@router.get("/channel-performance")
def channel_performance(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Compare email vs call outreach effectiveness."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # -- Email metrics --
    email_sent = (
        db.query(func.count(CallCampaign.id))
        .filter(
            CallCampaign.user_id == user.id,
            CallCampaign.email_sent_at.isnot(None),
            CallCampaign.email_sent_at >= cutoff,
        )
        .scalar()
    ) or 0

    # Count opens and replies from email_events linked via campaign
    email_opened = 0
    email_replied = 0
    if email_sent > 0:
        campaign_ids = (
            db.query(CallCampaign.id)
            .filter(
                CallCampaign.user_id == user.id,
                CallCampaign.email_sent_at.isnot(None),
                CallCampaign.email_sent_at >= cutoff,
            )
            .subquery()
        )
        email_opened = (
            db.query(func.count(func.distinct(EmailEvent.campaign_id)))
            .filter(
                EmailEvent.campaign_id.in_(
                    db.query(campaign_ids.c.id)
                ),
                EmailEvent.event_type == "email.opened",
            )
            .scalar()
        ) or 0
        email_replied = (
            db.query(func.count(func.distinct(EmailEvent.campaign_id)))
            .filter(
                EmailEvent.campaign_id.in_(
                    db.query(campaign_ids.c.id)
                ),
                EmailEvent.event_type == "email.replied",
            )
            .scalar()
        ) or 0

    email_open_rate = round(email_opened / email_sent * 100, 1) if email_sent > 0 else 0.0
    email_reply_rate = round(email_replied / email_sent * 100, 1) if email_sent > 0 else 0.0

    # -- Call metrics --
    call_attempted = (
        db.query(func.count(CallLog.id))
        .filter(CallLog.user_id == user.id, CallLog.created_at >= cutoff)
        .scalar()
    ) or 0

    call_connected = (
        db.query(func.count(CallLog.id))
        .filter(
            CallLog.user_id == user.id,
            CallLog.created_at >= cutoff,
            CallLog.outcome == "connected",
        )
        .scalar()
    ) or 0

    call_rate = round(call_connected / call_attempted * 100, 1) if call_attempted > 0 else 0.0

    return {
        "days": days,
        "email": {
            "sent": email_sent,
            "opened": email_opened,
            "replied": email_replied,
            "open_rate": email_open_rate,
            "reply_rate": email_reply_rate,
        },
        "call": {
            "attempted": call_attempted,
            "connected": call_connected,
            "rate": call_rate,
        },
    }


@router.get("/activity-timeline")
def activity_timeline(
    days: int = Query(30, ge=1, le=365),
    granularity: str = Query("day"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Time-series of daily or weekly activity."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    if granularity == "week":
        trunc_fn = func.date_trunc("week", Match.created_at)
        email_trunc = func.date_trunc("week", CallCampaign.email_sent_at)
        call_trunc = func.date_trunc("week", CallLog.created_at)
    else:
        trunc_fn = func.date_trunc("day", Match.created_at)
        email_trunc = func.date_trunc("day", CallCampaign.email_sent_at)
        call_trunc = func.date_trunc("day", CallLog.created_at)

    # Matches found per period
    match_rows = (
        db.query(
            cast(trunc_fn, sa_date_type()).label("date"),
            func.count(Match.id).label("count"),
        )
        .filter(Match.user_id == user.id, Match.created_at >= cutoff)
        .group_by("date")
        .all()
    )
    matches_by_date = {str(row.date): row.count for row in match_rows}

    # Emails sent per period
    email_rows = (
        db.query(
            cast(email_trunc, sa_date_type()).label("date"),
            func.count(CallCampaign.id).label("count"),
        )
        .filter(
            CallCampaign.user_id == user.id,
            CallCampaign.email_sent_at.isnot(None),
            CallCampaign.email_sent_at >= cutoff,
        )
        .group_by("date")
        .all()
    )
    emails_by_date = {str(row.date): row.count for row in email_rows}

    # Calls per period
    call_rows = (
        db.query(
            cast(call_trunc, sa_date_type()).label("date"),
            func.count(CallLog.id).label("count"),
        )
        .filter(CallLog.user_id == user.id, CallLog.created_at >= cutoff)
        .group_by("date")
        .all()
    )
    calls_by_date = {str(row.date): row.count for row in call_rows}

    # Merge all dates
    all_dates = sorted(
        set(matches_by_date.keys()) | set(emails_by_date.keys()) | set(calls_by_date.keys())
    )

    timeline = [
        {
            "date": d,
            "matches_found": matches_by_date.get(d, 0),
            "emails_sent": emails_by_date.get(d, 0),
            "calls_made": calls_by_date.get(d, 0),
        }
        for d in all_dates
    ]

    return {"days": days, "granularity": granularity, "timeline": timeline}


@router.get("/score-distribution")
def score_distribution(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Histogram of match composite_score in 10-point buckets."""
    # Build bucket boundaries
    buckets = []
    for low in range(0, 100, 10):
        high = low + 10
        label = f"{low}-{high}"

        count = (
            db.query(func.count(Match.id))
            .filter(
                Match.user_id == user.id,
                Match.composite_score >= low,
                Match.composite_score < high,
            )
            .scalar()
        ) or 0

        buckets.append({"bucket": label, "count": count})

    return {"buckets": buckets}


# ── Helpers ─────────────────────────────────────────────────────────

def sa_date_type():
    """Return SQLAlchemy Date type for casting."""
    from sqlalchemy import Date
    return Date
