"""Autopilot — one-click pipeline that ingests, scores, researches, and creates campaigns.

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

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.call_campaign import CallCampaign
from ..models.contact import Contact
from ..models.match import Match
from ..models.research import ResearchResult

logger = logging.getLogger(__name__)

# Module-level state for status reporting
_last_run: datetime | None = None
_last_result: dict[str, Any] | None = None
_running: bool = False


def get_autopilot_status() -> dict[str, Any]:
    """Return the current autopilot status."""
    return {
        "last_run": _last_run.isoformat() if _last_run else None,
        "last_result": _last_result,
        "running": _running,
    }


def _get_top_unresearched(db: Session, limit: int = 5) -> list[Match]:
    """Fetch the top-scoring matches that have no research yet."""
    researched_ids = (
        db.query(ResearchResult.match_id)
        .subquery()
    )
    return (
        db.query(Match)
        .filter(
            Match.hard_filter_pass == "pass",
            Match.composite_score > 0,
            ~Match.id.in_(db.query(researched_ids.c.match_id)),
        )
        .order_by(Match.composite_score.desc())
        .limit(limit)
        .all()
    )


def _get_new_contacts_without_campaigns(db: Session) -> list[Contact]:
    """Find contacts that have no campaign associated with them yet."""
    campaign_contact_ids = (
        db.query(CallCampaign.contact_id)
        .subquery()
    )
    return (
        db.query(Contact)
        .filter(
            Contact.source == "exa",
            ~Contact.id.in_(db.query(campaign_contact_ids.c.contact_id)),
        )
        .order_by(Contact.created_at.desc())
        .limit(20)
        .all()
    )


def _find_best_match_for_company(db: Session, company: str) -> Match | None:
    """Find the highest-scored match for a given company."""
    return (
        db.query(Match)
        .join(Match.opportunity)
        .filter(
            Match.hard_filter_pass == "pass",
            Match.opportunity.has(company=company),
        )
        .order_by(Match.composite_score.desc())
        .first()
    )


async def run_autopilot_cycle(db: Session) -> dict[str, int]:
    """Execute one complete autopilot cycle.

    Returns:
        Dict with counts: ingest, scored, researched, campaigns_created.
    """
    global _last_run, _last_result, _running

    if _running:
        return {"error": "Autopilot cycle already in progress"}

    _running = True
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

            results["ingest"] = await run_all_connectors(db)
            logger.info("Autopilot ingest: %d new opportunities", results["ingest"])
        except Exception as e:
            logger.error("Autopilot ingest failed: %s", e)

        # --- Step 2: Score all matches ---
        try:
            from .match_engine import score_all_matches

            score_result = await score_all_matches(db)
            results["scored"] = score_result.get("scored", 0)
            logger.info("Autopilot scoring: %d matches scored", results["scored"])
        except Exception as e:
            logger.error("Autopilot scoring failed: %s", e)

        # --- Step 3: Deep-research top unresearched matches ---
        top_matches = _get_top_unresearched(db, limit=5)
        for match in top_matches:
            try:
                from .research.engine import deep_research

                await deep_research(db, match)
                results["researched"] += 1
                logger.info(
                    "Autopilot researched match %s (%s at %s)",
                    match.id,
                    match.opportunity.title,
                    match.opportunity.company,
                )
            except Exception as e:
                logger.error(
                    "Autopilot research failed for match %s: %s",
                    match.id, e,
                )

        # --- Step 4: Create campaigns for new research-backed contacts ---
        new_contacts = _get_new_contacts_without_campaigns(db)
        for contact in new_contacts:
            match = _find_best_match_for_company(db, contact.company)
            if not match:
                continue

            campaign = CallCampaign(
                match_id=match.id,
                contact_id=contact.id,
                status="pending",
            )
            db.add(campaign)
            db.flush()

            try:
                from .outreach_gen import generate_outreach_package

                pkg = await generate_outreach_package(db, campaign)
                campaign.script_json = pkg.get("call_script")
                campaign.email_draft = pkg.get("email_draft", "")
                campaign.email_subject = pkg.get("email_subject", "")
                campaign.linkedin_msg = pkg.get("linkedin_message", "")
                campaign.outreach_sequence = ",".join(
                    pkg.get("suggested_sequence", [])
                )
                results["campaigns_created"] += 1
                logger.info(
                    "Autopilot created campaign for %s at %s",
                    contact.name,
                    contact.company,
                )
            except Exception as e:
                logger.error(
                    "Autopilot outreach gen failed for contact %s: %s",
                    contact.id, e,
                )

        db.commit()

    finally:
        _running = False
        _last_run = datetime.utcnow()
        _last_result = results

    return results
