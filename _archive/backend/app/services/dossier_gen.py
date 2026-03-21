from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.dossier import Dossier
from ..models.match import Match
from ..models.profile import Profile
from . import gemini

logger = logging.getLogger(__name__)


def _extract_sections(content_md: str) -> dict[str, str]:
    """Extract named sections from markdown content."""
    sections: dict[str, str] = {}
    section_names = [
        "company_background", "role_analysis", "fit_assessment",
        "talking_points", "concerns", "suggested_approach",
    ]
    parts = content_md.split("## ")
    for i, part in enumerate(parts[1:]):  # Skip content before first ##
        if i < len(section_names):
            lines = part.split("\n", 1)
            sections[section_names[i]] = lines[1].strip() if len(lines) > 1 else ""
    return sections


async def generate_dossier(
    db: Session, match: Match, *, user_id: UUID | None = None
) -> Dossier:
    # Resolve user_id from match if not provided explicitly
    resolved_user_id = user_id or match.user_id

    existing = (
        db.query(Dossier)
        .filter(Dossier.match_id == match.id, Dossier.user_id == resolved_user_id)
        .first()
    )
    if existing:
        return existing

    profile = (
        db.query(Profile)
        .filter(Profile.id == match.profile_id, Profile.user_id == resolved_user_id)
        .first()
    )
    opportunity = match.opportunity

    prompt = f"""Generate a comprehensive briefing dossier for a job match.

CANDIDATE:
Name: {profile.name}
Summary: {profile.summary}
Skills: {', '.join(s.name for s in profile.skills)}
Experience: {', '.join(f'{e.title} at {e.company}' for e in profile.experiences)}

JOB OPPORTUNITY:
Title: {opportunity.title}
Company: {opportunity.company}
Location: {opportunity.location or 'Not specified'}
Description: {(opportunity.description or '')[:3000]}

Match Score: {match.composite_score}/100
Rationale: {match.rationale or 'N/A'}

Write the briefing in markdown with these sections:
## Company Background
## Role Analysis
## Fit Assessment
## Talking Points
## Potential Concerns
## Suggested Approach"""

    content_md = await gemini.generate_text(
        prompt,
        system="You are a career intelligence analyst. Write detailed, actionable briefings.",
    )

    sections = _extract_sections(content_md)

    dossier = Dossier(
        user_id=resolved_user_id,
        match_id=match.id,
        content_md=content_md,
        sections_json=sections,
    )
    db.add(dossier)
    db.commit()
    db.refresh(dossier)
    return dossier


async def generate_enriched_dossier(
    db: Session,
    match: Match,
    company_intel: dict[str, Any],
    contacts: list[dict[str, Any]],
    *,
    user_id: UUID | None = None,
) -> Dossier:
    """Generate a dossier enriched with deep research data.

    If a dossier already exists for this match, it is replaced with
    the enriched version. Falls back to the standard dossier generator
    if research data is insufficient.

    Args:
        db: Active database session.
        match: The Match to generate a dossier for.
        company_intel: Structured company research from Gemini Search.
        contacts: Contact list from Exa discovery.
        user_id: The owning user's ID for scoped queries.

    Returns:
        The created or updated Dossier.
    """
    # Resolve user_id from match if not provided explicitly
    resolved_user_id = user_id or match.user_id

    profile = (
        db.query(Profile)
        .filter(Profile.id == match.profile_id, Profile.user_id == resolved_user_id)
        .first()
    )
    opportunity = match.opportunity

    # If research data is empty/errored, fall back to standard dossier
    has_useful_intel = (
        isinstance(company_intel, dict)
        and company_intel.get("company_overview")
        and company_intel.get("company_overview") != "Unknown"
        and "error" not in company_intel.get("company_overview", "").lower()
    )
    if not has_useful_intel:
        return await generate_dossier(db, match, user_id=resolved_user_id)

    # Build enriched prompt with research data
    intel_summary = (
        f"Company Overview: {company_intel.get('company_overview', 'N/A')}\n"
        f"Recent News: {json.dumps(company_intel.get('recent_news', []))}\n"
        f"Funding: {company_intel.get('funding', 'N/A')}\n"
        f"Leadership: {json.dumps(company_intel.get('leadership', []))}\n"
        f"Culture: {company_intel.get('culture', 'N/A')}\n"
        f"Hiring Activity: {company_intel.get('hiring_activity', 'N/A')}\n"
        f"Company Size: {company_intel.get('company_size', 'N/A')}\n"
        f"Tech Stack: {company_intel.get('tech_stack', 'N/A')}\n"
    )

    contacts_summary = ""
    if contacts:
        contact_lines = [
            f"  - {c.get('name', 'Unknown')}: {c.get('title', 'N/A')} ({c.get('url', '')})"
            for c in contacts[:10]
        ]
        contacts_summary = f"Discovered Contacts:\n" + "\n".join(contact_lines)

    prompt = f"""Generate a comprehensive, research-backed briefing dossier for a job match.

CANDIDATE:
Name: {profile.name}
Summary: {profile.summary}
Skills: {', '.join(s.name for s in profile.skills)}
Experience: {', '.join(f'{e.title} at {e.company}' for e in profile.experiences)}

JOB OPPORTUNITY:
Title: {opportunity.title}
Company: {opportunity.company}
Location: {opportunity.location or 'Not specified'}
Description: {(opportunity.description or '')[:3000]}

Match Score: {match.composite_score}/100
Rationale: {match.rationale or 'N/A'}

DEEP RESEARCH INTEL:
{intel_summary}

{contacts_summary}

Using the research intel above, write a detailed briefing in markdown with these sections:
## Company Background
Use the research data to give a thorough, current overview. Mention recent news, funding, and leadership.

## Role Analysis
Analyze the role in context of the company's current situation (hiring activity, tech stack, team growth).

## Fit Assessment
Map the candidate's skills and experience to the role requirements. Be specific about which skills match.

## Talking Points
Create 5-7 talking points that reference SPECIFIC research findings. E.g., "Reference their recent Series B to show you follow the company."

## Key Contacts
List the discovered contacts with suggested approach for each.

## Potential Concerns
Honest assessment of gaps or risks.

## Suggested Approach
Step-by-step outreach strategy using the research and contact information."""

    content_md = await gemini.generate_text(
        prompt,
        system=(
            "You are a career intelligence analyst with access to deep company research. "
            "Write detailed, actionable briefings that leverage specific research findings. "
            "Every recommendation should be grounded in the research data provided."
        ),
    )

    sections = _extract_sections(content_md)

    # Replace existing dossier if one exists
    existing = (
        db.query(Dossier)
        .filter(Dossier.match_id == match.id, Dossier.user_id == resolved_user_id)
        .first()
    )
    if existing:
        existing.content_md = content_md
        existing.sections_json = sections
        db.commit()
        db.refresh(existing)
        return existing

    dossier = Dossier(
        user_id=resolved_user_id,
        match_id=match.id,
        content_md=content_md,
        sections_json=sections,
    )
    db.add(dossier)
    db.commit()
    db.refresh(dossier)
    return dossier
