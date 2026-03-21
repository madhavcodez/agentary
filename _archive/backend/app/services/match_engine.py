from __future__ import annotations

import asyncio
import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.match import Match
from ..models.opportunity import Opportunity
from ..models.profile import Profile
from . import gemini, qdrant_store

logger = logging.getLogger(__name__)

_LLM_BATCH_SIZE = 10

HARD_FILTER_CONFIG = {
    "role_families": ["ai", "ml", "machine learning", "full stack", "software engineer", "backend", "frontend", "data"],
    "exclude_seniority": ["staff", "principal", "director", "vp", "vice president", "head of", "lead"],
    "experience_max": 3,
}


def _passes_hard_filter(title: str, description: str | None) -> bool:
    title_lower = title.lower()

    # Check excluded seniority
    for excluded in HARD_FILTER_CONFIG["exclude_seniority"]:
        if excluded in title_lower:
            return False

    # Check role family match (word boundary aware)
    def _has_role(text: str) -> bool:
        for role in HARD_FILTER_CONFIG["role_families"]:
            pattern = r"\b" + re.escape(role) + r"\b"
            if re.search(pattern, text):
                return True
        return False

    role_match = _has_role(title_lower)
    if not role_match:
        desc_lower = (description or "").lower()
        role_match = _has_role(desc_lower[:500])

    # Check years of experience (if mentioned in title/desc)
    yoe_pattern = r"(\d+)\+?\s*(?:years?|yrs?)"
    for text in [title_lower, (description or "").lower()[:1000]]:
        matches = re.findall(yoe_pattern, text)
        for m in matches:
            if int(m) > HARD_FILTER_CONFIG["experience_max"] + 2:
                return False

    return role_match


async def score_all_matches(db: Session, *, user_id: UUID) -> dict:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        return {"error": "No profile found. Upload a resume first."}

    opportunities = (
        db.query(Opportunity)
        .filter(Opportunity.user_id == user_id)
        .all()
    )
    if not opportunities:
        return {"error": "No opportunities found. Run ingest first."}

    # Get profile embedding for semantic search
    profile_embedding = None
    if profile.resume_text:
        profile_embedding = await gemini.embed_text(profile.resume_text, task_type="RETRIEVAL_QUERY")

    scored = 0
    llm_scored_in_batch = 0

    for opp in opportunities:
        existing = db.query(Match).filter(
            Match.opportunity_id == opp.id,
            Match.profile_id == profile.id,
            Match.user_id == user_id,
        ).first()
        if existing:
            continue

        # Hard filter
        passes = _passes_hard_filter(opp.title, opp.description)

        match = Match(
            user_id=user_id,
            opportunity_id=opp.id,
            profile_id=profile.id,
            hard_filter_pass="pass" if passes else "fail",
            status="new",
        )

        if passes and profile_embedding:
            # Semantic score via Qdrant (only for embedded opps)
            if opp.embedding_id:
                try:
                    results = qdrant_store.search_similar(
                        "secretairy_opportunities", profile_embedding, limit=50
                    )
                    for r in results:
                        if r["id"] == str(opp.id):
                            match.semantic_score = r["score"]
                            break
                except Exception as e:
                    logger.warning("Semantic scoring failed for %s: %s", opp.id, e)

            # LLM score for ALL passing opportunities (batched to avoid rate limits)
            try:
                prompt = f"""Rate how well this job matches this candidate on a scale of 0.0 to 1.0.

CANDIDATE:
Name: {profile.name}
Summary: {profile.summary}
Skills: {', '.join(s.name for s in profile.skills)}
Experience: {', '.join(f'{e.title} at {e.company}' for e in profile.experiences)}

JOB:
Title: {opp.title}
Company: {opp.company}
Location: {opp.location or 'Not specified'}
Description: {(opp.description or '')[:1500]}

Return JSON: {{"score": 0.0-1.0, "rationale": "brief explanation"}}"""

                result = await gemini.generate_structured(prompt)
                match.llm_score = float(result.get("score", 0.0))
                match.rationale = result.get("rationale", "")
                llm_scored_in_batch += 1

                # Rate-limit: pause between batches
                if llm_scored_in_batch % _LLM_BATCH_SIZE == 0:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.warning("LLM scoring failed for %s: %s", opp.id, e)

            # Composite score
            sem = match.semantic_score or 0.0
            llm = match.llm_score or 0.0
            match.composite_score = round((sem * 0.3 + llm * 0.7) * 100, 1)

        db.add(match)
        scored += 1

    db.commit()
    return {"scored": scored, "total_opportunities": len(opportunities)}
