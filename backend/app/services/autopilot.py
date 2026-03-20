"""Autopilot -- one-click pipeline that ingests, scores, researches, and creates campaigns.

A single call to ``run_autopilot_cycle`` performs:
1. Ingest new job opportunities from all connectors.
2. Score all unscored matches (no artificial cap).
3. Deep-research the top unresearched matches.
4. Create outreach campaigns for newly discovered contacts.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.call_campaign import CallCampaign
from ..models.contact import Contact
from ..models.match import Match
from ..models.research import ResearchResult

logger = logging.getLogger(__name__)

# Module-level state for status reporting, keyed by user_id string
_user_status: dict[str, dict[str, Any]] = {}


def get_autopilot_status(*, user_id: UUID) -> dict[str, Any]:
    """Return the current autopilot status for a specific user."""
    uid = str(user_id)
    status = _user_status.get(uid, {})
    return {
        "last_run": status.get("last_run"),
        "last_result": status.get("last_result"),
        "running": status.get("running", False),
    }


def _get_top_unresearched(
    db: Session, user_id: UUID, limit: int = 5
) -> list[Match]:
    """Fetch the top-scoring matches that have no research yet."""
    researched_ids = (
        db.query(ResearchResult.match_id)
        .filter(ResearchResult.user_id == user_id)
        .subquery()
    )
    return (
        db.query(Match)
        .filter(
            Match.user_id == user_id,
            Match.hard_filter_pass == "pass",
            Match.composite_score > 0,
            ~Match.id.in_(db.query(researched_ids.c.match_id)),
        )
        .order_by(Match.composite_score.desc())
        .limit(limit)
        .all()
    )


def _get_new_contacts_without_campaigns(
    db: Session, user_id: UUID
) -> list[Contact]:
    """Find contacts that have no campaign associated with them yet."""
    campaign_contact_ids = (
        db.query(CallCampaign.contact_id)
        .filter(CallCampaign.user_id == user_id)
        .subquery()
    )
    return (
        db.query(Contact)
        .filter(
            Contact.user_id == user_id,
            Contact.source == "exa",
            ~Contact.id.in_(db.query(campaign_contact_ids.c.contact_id)),
        )
        .order_by(Contact.created_at.desc())
        .limit(20)
        .all()
    )


def _find_best_match_for_company(
    db: Session, user_id: UUID, company: str
) -> Match | None:
    """Find the highest-scored match for a given company."""
    return (
        db.query(Match)
        .join(Match.opportunity)
        .filter(
            Match.user_id == user_id,
            Match.hard_filter_pass == "pass",
            Match.opportunity.has(company=company),
        )
        .order_by(Match.composite_score.desc())
        .first()
    )


async def run_autopilot_cycle(
    db: Session, *, user_id: UUID
) -> dict[str, int]:
    """Execute one complete autopilot cycle for a specific user.

    Returns:
        Dict with counts: ingest, scored, researched, campaigns_created.
    """
    uid = str(user_id)

    # Initialize user status if not present
    if uid not in _user_status:
        _user_status[uid] = {}

    if _user_status[uid].get("running"):
        return {"error": "Autopilot cycle already in progress"}

    _user_status[uid]["running"] = True
    results: dict[str, int] = {
        "ingest": 0,
        "scored": 0,
        "researched": 0,
        "campaigns_created": 0,
    }

    try:
        # --- Step 1: Ingest new opportunities ---
        try:
            from .ingest.runner import run_all_connectors

            results["ingest"] = await run_all_connectors(db, user_id=user_id)
            logger.info(
                "Autopilot ingest: %d new opportunities (user=%s)",
                results["ingest"], uid,
            )
        except Exception as e:
            logger.error("Autopilot ingest failed (user=%s): %s", uid, e)

        # --- Step 2: Score all matches ---
        try:
            from .match_engine import score_all_matches

            score_result = await score_all_matches(db, user_id=user_id)
            results["scored"] = score_result.get("scored", 0)
            logger.info(
                "Autopilot scoring: %d matches scored (user=%s)",
                results["scored"], uid,
            )
        except Exception as e:
            logger.error("Autopilot scoring failed (user=%s): %s", uid, e)

        # --- Step 3: Deep-research top unresearched matches ---
        top_matches = _get_top_unresearched(db, user_id, limit=5)
        for match in top_matches:
            try:
                from .research.engine import deep_research

                await deep_research(db, match, user_id=user_id)
                results["researched"] += 1
                logger.info(
                    "Autopilot researched match %s (%s at %s) (user=%s)",
                    match.id,
                    match.opportunity.title,
                    match.opportunity.company,
                    uid,
                )
            except Exception as e:
                logger.error(
                    "Autopilot research failed for match %s (user=%s): %s",
                    match.id, uid, e,
                )

        # --- Step 4: Create campaigns for new research-backed contacts ---
        new_contacts = _get_new_contacts_without_campaigns(db, user_id)
        for contact in new_contacts:
            match = _find_best_match_for_company(db, user_id, contact.company)
            if not match:
                continue

            campaign = CallCampaign(
                user_id=user_id,
                match_id=match.id,
                contact_id=contact.id,
                status="pending",
            )
            db.add(campaign)
            db.flush()

            try:
                from .outreach_gen import generate_outreach_package

                pkg = await generate_outreach_package(
                    db, campaign, user_id=user_id
                )
                campaign.script_json = pkg.get("call_script")
                campaign.email_draft = pkg.get("email_draft", "")
                campaign.email_subject = pkg.get("email_subject", "")
                campaign.linkedin_msg = pkg.get("linkedin_message", "")
                campaign.outreach_sequence = ",".join(
                    pkg.get("suggested_sequence", [])
                )
                results["campaigns_created"] += 1
                logger.info(
                    "Autopilot created campaign for %s at %s (user=%s)",
                    contact.name,
                    contact.company,
                    uid,
                )
            except Exception as e:
                logger.error(
                    "Autopilot outreach gen failed for contact %s (user=%s): %s",
                    contact.id, uid, e,
                )

        db.commit()

    finally:
        _user_status[uid]["running"] = False
        _user_status[uid]["last_run"] = datetime.utcnow().isoformat()
        _user_status[uid]["last_result"] = results

    return results
