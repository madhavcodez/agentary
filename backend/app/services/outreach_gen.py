"""Multi-channel outreach content generator.

Generates personalized call scripts, email drafts, and LinkedIn messages
for a campaign, using research data and profile context. Every piece of
content is uniquely crafted per opportunity — no templates.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models.call_campaign import CallCampaign
from ..models.contact import Contact
from ..models.match import Match
from ..models.opportunity import Opportunity
from ..models.profile import Profile
from ..models.research import ResearchResult
from .gemini import generate_structured, generate_text

logger = logging.getLogger(__name__)


def _build_context(
    profile: Profile | None,
    opp: Opportunity,
    contact: Contact | None,
    research: ResearchResult | None,
) -> str:
    """Build a rich context string for outreach generation prompts."""
    parts: list[str] = []

    if profile:
        skills_str = ", ".join(s.name for s in profile.skills) if profile.skills else "N/A"
        exp_str = (
            "; ".join(f"{e.title} at {e.company}" for e in profile.experiences)
            if profile.experiences
            else "N/A"
        )
        parts.append(
            f"CANDIDATE:\n"
            f"  Name: {profile.name}\n"
            f"  Summary: {profile.summary or 'N/A'}\n"
            f"  Skills: {skills_str}\n"
            f"  Experience: {exp_str}\n"
        )

    parts.append(
        f"TARGET OPPORTUNITY:\n"
        f"  Company: {opp.company}\n"
        f"  Role: {opp.title}\n"
        f"  Location: {opp.location or 'Not specified'}\n"
        f"  Description excerpt: {(opp.description or '')[:1500]}\n"
    )

    if contact:
        parts.append(
            f"CONTACT:\n"
            f"  Name: {contact.name or 'Unknown'}\n"
            f"  Title: {contact.title or 'Unknown'}\n"
            f"  Company: {contact.company}\n"
        )

    if research and isinstance(research.company_intel, dict):
        intel = research.company_intel
        parts.append(
            f"COMPANY INTEL (from research):\n"
            f"  Overview: {intel.get('company_overview', 'N/A')}\n"
            f"  Recent news: {json.dumps(intel.get('recent_news', []))}\n"
            f"  Funding: {intel.get('funding', 'N/A')}\n"
            f"  Culture: {intel.get('culture', 'N/A')}\n"
            f"  Hiring activity: {intel.get('hiring_activity', 'N/A')}\n"
            f"  Tech stack: {intel.get('tech_stack', 'N/A')}\n"
        )

    return "\n".join(parts)


_CALL_SCRIPT_SCHEMA = """{
  "opener": "string — warm opening line mentioning the role and company",
  "gatekeeper_script": "string — what to say to a receptionist",
  "pitch_points": ["string — key strength relevant to this role"],
  "voicemail_script": "string — concise voicemail under 30 seconds",
  "scheduling_prompts": ["string — flexible time offering"],
  "objection_handlers": {"objection": "response"},
  "callback_number": "string"
}"""

_EMAIL_SCHEMA = """{
  "subject": "string — compelling subject line under 60 chars",
  "body": "string — full email body in plain text"
}"""


async def _gen_call_script(context: str) -> dict[str, Any]:
    """Generate a structured call script."""
    prompt = f"""Generate a cold-call script for an AI assistant calling on behalf of a job candidate.

{context}

Instructions:
- The opener should reference a SPECIFIC recent news item or company detail from the research.
- The gatekeeper script should be polite, mentioning the specific role name.
- Include 3-4 pitch points that directly map candidate skills to role requirements.
- Voicemail should be under 30 seconds when spoken. Include the role name and one standout skill.
- Scheduling prompts should offer 2 flexible time options.
- Include 2-3 common objection handlers (e.g., "we're not hiring", "send a resume").
- Callback number: use candidate phone or +1-000-000-0000 as placeholder.

Return ONLY valid JSON matching this schema:
{_CALL_SCRIPT_SCHEMA}"""

    return await generate_structured(prompt, schema_hint=_CALL_SCRIPT_SCHEMA)


async def _gen_email_draft(context: str) -> dict[str, Any]:
    """Generate a personalized email draft."""
    prompt = f"""Write a personalized cold outreach email from a job candidate to a contact at a company about a specific role.

{context}

Instructions:
- Subject line: compelling, under 60 characters, NOT generic ("RE:", "Following up" etc.)
- Reference SPECIFIC company intel (a recent news item, funding round, product launch, or cultural value).
- Show you have done your homework — mention something only someone who researched the company would know.
- Highlight 2-3 candidate strengths that directly align with the role.
- Be concise: 150-250 words max.
- Professional but warm tone. Not stiff, not overly casual.
- End with a clear, low-pressure CTA (e.g., "Would a 15-minute call this week work?").
- Do NOT use placeholder brackets like [Name] — use actual names from the context.

Return JSON with "subject" and "body" keys."""

    return await generate_structured(prompt, schema_hint=_EMAIL_SCHEMA)


async def _gen_linkedin_message(context: str) -> str:
    """Generate a short LinkedIn connection message."""
    prompt = f"""Write a LinkedIn connection request message from a job candidate to a hiring contact.

{context}

Instructions:
- STRICT 300 character limit (LinkedIn enforces this).
- Reference something specific: a mutual interest, the role, or a company achievement.
- Be genuine, not salesy.
- Do NOT include "Dear" or formal greetings — LinkedIn messages are casual.
- End with a single clear ask.

Return ONLY the message text, no JSON, no quotes around it."""

    text = await generate_text(
        prompt,
        system="You write concise, personalized LinkedIn messages. Stay under 300 characters.",
    )

    # Enforce the 300 char limit
    message = text.strip().strip('"').strip("'")
    if len(message) > 300:
        # Truncate at the last full sentence within 300 chars
        truncated = message[:297]
        last_period = truncated.rfind(".")
        if last_period > 200:
            message = truncated[: last_period + 1]
        else:
            message = truncated + "..."

    return message


async def generate_outreach_package(
    db: Session, campaign: CallCampaign
) -> dict[str, Any]:
    """Generate all 3 outreach channels for a campaign.

    Produces a call script, email draft, and LinkedIn message in
    parallel using Gemini, personalized with research data.

    Args:
        db: Active database session.
        campaign: The CallCampaign to generate content for.

    Returns:
        Dict with call_script, email_subject, email_draft,
        linkedin_message, and suggested_sequence.
    """
    match: Match | None = (
        db.query(Match).filter(Match.id == campaign.match_id).first()
    )
    if not match:
        raise ValueError(f"Match {campaign.match_id} not found for campaign")

    opp = match.opportunity
    profile = db.query(Profile).first()
    contact: Contact | None = (
        db.query(Contact).filter(Contact.id == campaign.contact_id).first()
    )
    research: ResearchResult | None = (
        db.query(ResearchResult)
        .filter(ResearchResult.match_id == campaign.match_id)
        .first()
    )

    context = _build_context(profile, opp, contact, research)

    # Generate all 3 channels in parallel
    call_script_result, email_result, linkedin_result = await asyncio.gather(
        _gen_call_script(context),
        _gen_email_draft(context),
        _gen_linkedin_message(context),
        return_exceptions=True,
    )

    # Handle any failures gracefully
    call_script: dict[str, Any] = (
        call_script_result
        if isinstance(call_script_result, dict)
        else {"error": str(call_script_result)}
    )

    email: dict[str, Any] = (
        email_result
        if isinstance(email_result, dict)
        else {"subject": f"Regarding the {opp.title} role", "body": str(email_result)}
    )

    linkedin: str = (
        linkedin_result
        if isinstance(linkedin_result, str)
        else f"Hi! Interested in the {opp.title} role at {opp.company}. Would love to connect."
    )

    return {
        "call_script": call_script,
        "email_subject": email.get("subject", f"Regarding the {opp.title} role"),
        "email_draft": email.get("body", ""),
        "linkedin_message": linkedin,
        "suggested_sequence": [
            "email",
            "wait_24h",
            "linkedin",
            "wait_48h",
            "call",
        ],
    }
