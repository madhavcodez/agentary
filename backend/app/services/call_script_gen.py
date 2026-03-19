from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models.call_campaign import CallCampaign
from ..models.dossier import Dossier
from ..models.match import Match
from ..models.opportunity import Opportunity
from ..models.profile import Profile
from . import gemini

logger = logging.getLogger(__name__)

_SCRIPT_SCHEMA = """{
  "opener": "string — warm opening line referencing the role and company",
  "gatekeeper_script": "string — what to say if a receptionist or gatekeeper answers",
  "pitch_points": ["string", "string", "string"],
  "voicemail_script": "string — concise voicemail message",
  "scheduling_prompts": ["string", "string"],
  "callback_number": "string — phone number to leave for callback"
}"""


async def generate_call_script(
    db: Session, campaign: CallCampaign
) -> dict[str, Any]:
    """Generate a structured call script using Gemini.

    Loads the match, opportunity, profile, and dossier associated with the
    campaign, then asks Gemini to produce a JSON call script.

    Args:
        db: Active database session.
        campaign: The CallCampaign to generate a script for.

    Returns:
        A dict matching the script schema.
    """
    match: Match | None = (
        db.query(Match).filter(Match.id == campaign.match_id).first()
    )
    if not match:
        raise ValueError(f"Match {campaign.match_id} not found")

    opportunity: Opportunity | None = (
        db.query(Opportunity)
        .filter(Opportunity.id == match.opportunity_id)
        .first()
    )
    profile: Profile | None = (
        db.query(Profile).filter(Profile.id == match.profile_id).first()
    )
    dossier: Dossier | None = (
        db.query(Dossier).filter(Dossier.match_id == match.id).first()
    )

    company = opportunity.company if opportunity else "the company"
    title = opportunity.title if opportunity else "the open position"
    description_snippet = ""
    if opportunity and opportunity.description:
        description_snippet = opportunity.description[:600]

    profile_summary = ""
    if profile:
        profile_summary = (
            f"Name: {profile.name}\n"
            f"Summary: {profile.summary or 'AI/ML engineer and full-stack developer'}\n"
        )

    dossier_excerpt = ""
    if dossier and dossier.content_md:
        dossier_excerpt = dossier.content_md[:800]

    contact_name = campaign.contact.name if campaign.contact else None
    contact_title = campaign.contact.title if campaign.contact else None

    prompt = f"""Generate a cold-call script for an AI assistant calling on behalf of a job candidate.

CANDIDATE PROFILE:
{profile_summary}

TARGET COMPANY: {company}
ROLE: {title}
CONTACT NAME: {contact_name or "Unknown"}
CONTACT TITLE: {contact_title or "Unknown"}

JOB DESCRIPTION EXCERPT:
{description_snippet}

RESEARCH DOSSIER EXCERPT:
{dossier_excerpt}

MATCH SCORE: {match.composite_score:.0%}

Instructions:
- The opener should be warm and professional, immediately stating purpose.
- The gatekeeper script should politely explain you are calling about a specific role.
- Pitch points should highlight 3 candidate strengths that match this role.
- Voicemail should be under 30 seconds when spoken aloud.
- Scheduling prompts should offer flexible times.
- Callback number should be the candidate's phone or +1-000-000-0000 as placeholder.

Return ONLY valid JSON matching the schema."""

    script = await gemini.generate_structured(prompt, schema_hint=_SCRIPT_SCHEMA)

    # Ensure required keys exist with sensible defaults
    defaults = {
        "opener": f"Hi, this is SecretAIRY calling on behalf of Madhav Chauhan about the {title} role at {company}.",
        "gatekeeper_script": f"I'm calling regarding the {title} position. Could I speak with the hiring manager?",
        "pitch_points": [
            "Strong AI/ML engineering background",
            "Full-stack development experience",
            "Relevant project portfolio",
        ],
        "voicemail_script": (
            f"Hi, this is a message on behalf of Madhav Chauhan regarding the "
            f"{title} role at {company}. Madhav is very interested and would love "
            f"to discuss further. Please call back at your earliest convenience."
        ),
        "scheduling_prompts": [
            "Would Tuesday or Wednesday work better for a brief call?",
            "I can work around your schedule — what time suits you?",
        ],
        "callback_number": "+1-000-000-0000",
    }
    for key, default_val in defaults.items():
        if key not in script or not script[key]:
            script[key] = default_val

    return script
