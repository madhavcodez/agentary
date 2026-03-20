"""Deep research engine -- orchestrates all research sources.

Runs Gemini Search grounding and Exa contact discovery in parallel,
stores results in the database, auto-creates Contact records, and
triggers enriched dossier generation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.contact import Contact
from ...models.match import Match
from ...models.research import ResearchResult
from ..contact_dedup import find_duplicates
from .exa_search import exa_find_contacts
from .gemini_search import gemini_research

logger = logging.getLogger(__name__)


def _calculate_quality(
    company_intel: dict[str, Any] | None,
    contacts: list[dict[str, Any]] | None,
) -> float:
    """Score research quality from 0.0 to 1.0 based on completeness."""
    score = 0.0

    if isinstance(company_intel, dict):
        # +0.1 for each non-empty, non-"Unknown" field
        fields = [
            "company_overview", "recent_news", "funding",
            "leadership", "culture", "hiring_activity",
            "company_size", "tech_stack",
        ]
        for field in fields:
            val = company_intel.get(field)
            if val and val != "Unknown" and val != []:
                score += 0.1

    if isinstance(contacts, list) and len(contacts) > 0:
        # Up to 0.2 for contacts (0.05 each, capped at 4)
        score += min(len(contacts), 4) * 0.05

    return round(min(score, 1.0), 2)


async def deep_research(
    db: Session, match: Match, *, user_id: UUID | None = None
) -> dict[str, Any]:
    """Run the full research pipeline for a match.

    1. Runs Gemini Search + Exa in parallel.
    2. Stores a ResearchResult row.
    3. Auto-creates Contact records from discovered people.
    4. Triggers enriched dossier generation.

    Args:
        db: Active database session.
        match: The Match to research (must have .opportunity loaded).
        user_id: The owning user's ID for scoped queries.

    Returns:
        Summary dict with company_intel and contacts_found count.
    """
    # Resolve user_id from match if not provided explicitly
    resolved_user_id = user_id or match.user_id

    opp = match.opportunity
    company = opp.company
    role = opp.title

    # Check for existing research
    existing = (
        db.query(ResearchResult)
        .filter(
            ResearchResult.match_id == match.id,
            ResearchResult.user_id == resolved_user_id,
        )
        .first()
    )
    if existing:
        return {
            "company_intel": existing.company_intel,
            "contacts_found": len(existing.contacts_found or []),
            "already_researched": True,
        }

    # Run all research sources in parallel
    company_intel_result, exa_contacts_result = await asyncio.gather(
        gemini_research(company, role),
        exa_find_contacts(company, role),
        return_exceptions=True,
    )

    # Handle exceptions from parallel tasks
    company_intel: dict[str, Any] = (
        company_intel_result
        if isinstance(company_intel_result, dict)
        else {"error": str(company_intel_result)}
    )
    exa_contacts: list[dict[str, Any]] = (
        exa_contacts_result
        if isinstance(exa_contacts_result, list)
        else []
    )

    sources_used = ["gemini"]
    if exa_contacts:
        sources_used.append("exa")

    quality = _calculate_quality(company_intel, exa_contacts)

    # Persist research result
    research = ResearchResult(
        user_id=resolved_user_id,
        match_id=match.id,
        company_intel=company_intel,
        contacts_found=exa_contacts,
        sources_used=sources_used,
        quality_score=quality,
        researched_at=datetime.utcnow(),
    )
    db.add(research)

    # Auto-create Contact records from discovered people (fuzzy dedup)
    created_contacts = 0
    for raw in exa_contacts:
        name = raw.get("name", "").strip()
        if not name:
            continue

        email = raw.get("email") or ""

        # Fuzzy duplicate detection replaces exact name match
        duplicates = find_duplicates(
            db,
            name=name,
            company=company,
            email=email or None,
            threshold=85,
            user_id=str(resolved_user_id) if resolved_user_id else None,
        )
        if duplicates:
            logger.debug(
                "Skipping duplicate contact '%s' at '%s' — matched %d existing",
                name, company, len(duplicates),
            )
            continue

        phone = raw.get("phone") or ""

        contact = Contact(
            user_id=resolved_user_id,
            company=company,
            name=name,
            title=raw.get("title", ""),
            phone=phone,
            email=email,
            source="exa",
            opportunity_id=opp.id,
            notes=raw.get("snippet", "")[:500],
        )
        db.add(contact)
        created_contacts += 1

    db.commit()

    # Generate enriched dossier using research data
    try:
        from ..dossier_gen import generate_enriched_dossier

        await generate_enriched_dossier(
            db, match, company_intel, exa_contacts, user_id=resolved_user_id
        )
    except Exception as e:
        logger.warning(
            "Enriched dossier generation failed for match %s: %s",
            match.id, e,
        )

    return {
        "company_intel": company_intel,
        "contacts_found": len(exa_contacts),
        "contacts_created": created_contacts,
        "quality_score": quality,
        "sources_used": sources_used,
    }
