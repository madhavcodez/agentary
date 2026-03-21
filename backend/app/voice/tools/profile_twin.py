from __future__ import annotations

PROFILE_DATA = {
    "name": "Madhav S Chauhan",
    "summary": "AI/ML engineer and full-stack developer building intelligent systems",
    "skills": ["Python", "TypeScript", "React", "FastAPI", "Machine Learning", "LLMs"],
    "experience": [
        "Built SoundScore, a cross-platform music logging app",
        "Created Agentary, an AI research platform",
        "Experience with Gemini, OpenAI, and vector databases",
    ],
    "preferences": {
        "role_type": "AI/ML or Full-Stack",
        "location": "Bay Area preferred, open to remote",
        "experience_level": "New grad / 0-3 YOE",
    },
}


async def query_profile(question: str) -> str:
    return (
        f"Profile for {PROFILE_DATA['name']}:\n"
        f"Summary: {PROFILE_DATA['summary']}\n"
        f"Key Skills: {', '.join(PROFILE_DATA['skills'])}\n"
        f"Experience: {'; '.join(PROFILE_DATA['experience'])}\n"
        f"Preferences: {PROFILE_DATA['preferences']}"
    )
