"""Seed script: Creates a demo profile and runs ingest + scoring."""
import asyncio
import sys
sys.path.insert(0, ".")

from app.database import SessionLocal, init_db
from app.services.profile_builder import build_profile
from app.services.ingest.runner import run_all_connectors
from app.services.match_engine import score_all_matches

DEMO_RESUME = """
Madhav S Chauhan
Bay Area, CA | madhav@example.com

SUMMARY
AI/ML engineer and full-stack developer with experience building intelligent systems,
cross-platform applications, and LLM-powered tools. Seeking new grad / entry-level
roles in AI/ML, machine learning engineering, or full-stack development.

EDUCATION
B.S. Computer Science - Expected 2026

SKILLS
Languages: Python, TypeScript, JavaScript, Swift, Kotlin, Go
Frameworks: FastAPI, React, Next.js, SwiftUI, Jetpack Compose
AI/ML: PyTorch, Transformers, LLMs (Gemini, OpenAI), Vector Databases (Qdrant)
Tools: Docker, PostgreSQL, Redis, Git, GitHub Actions

EXPERIENCE
Personal Projects (2024-2026)
- SoundScore: Cross-platform music logging app (iOS + Android) with SwiftUI and Kotlin
- SecretAIRY: AI chief-of-staff system with job matching, dossier generation, and voice
- Edward: AI scheduling assistant with Google Calendar integration and voice (Pipecat)
- ReqChain: Multi-project AI requirements platform with FastAPI and Next.js

INTERESTS
- Building AI agents and multi-agent systems
- Voice AI and conversational interfaces
- Cross-platform mobile development
- Open source
"""


async def main():
    init_db()
    session = SessionLocal()

    try:
        print("=== Step 1: Building profile from resume ===")
        profile = await build_profile(session, DEMO_RESUME)
        print(f"Profile created: {profile.name} ({len(profile.skills)} skills, {len(profile.experiences)} experiences)")

        print("\n=== Step 2: Ingesting opportunities ===")
        count = await run_all_connectors(session)
        print(f"Ingested {count} new opportunities")

        print("\n=== Step 3: Scoring matches ===")
        result = await score_all_matches(session)
        print(f"Scoring result: {result}")

        # Show top matches
        from app.models.match import Match
        from sqlalchemy.orm import joinedload
        top_matches = (
            session.query(Match)
            .options(joinedload(Match.opportunity))
            .filter(Match.composite_score > 0)
            .order_by(Match.composite_score.desc())
            .limit(5)
            .all()
        )
        print(f"\n=== Top {len(top_matches)} Matches ===")
        for m in top_matches:
            opp = m.opportunity
            print(f"  [{m.composite_score:.1f}] {opp.title} at {opp.company} ({opp.source})")
            if m.rationale:
                print(f"         {m.rationale[:100]}...")

        # Generate dossiers for top 3
        if top_matches:
            print("\n=== Step 4: Generating dossiers for top 3 ===")
            from app.services.dossier_gen import generate_dossier
            for m in top_matches[:3]:
                try:
                    dossier = await generate_dossier(session, m)
                    print(f"  Dossier for {m.opportunity.title}: {len(dossier.content_md)} chars")
                except Exception as e:
                    print(f"  Dossier failed for {m.opportunity.title}: {e}")

        print("\n=== Seed complete! ===")

    finally:
        session.close()


if __name__ == "__main__":
    asyncio.run(main())
