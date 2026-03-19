import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_build_profile(db):
    mock_structured = {
        "name": "Test User",
        "email": "test@example.com",
        "summary": "A test engineer",
        "skills": [{"name": "Python", "category": "languages", "proficiency": "expert"}],
        "experiences": [{"company": "TestCorp", "title": "Engineer", "description": "Built things"}],
        "preferences": [{"key": "location_pref", "value": "remote"}],
    }

    # Delete existing profile data to avoid FK conflicts
    from app.models.dossier import Dossier
    from app.models.match import Match
    from app.models.profile import Experience, Preference, Profile, Skill

    db.query(Dossier).delete()
    db.query(Match).delete()
    db.query(Preference).delete()
    db.query(Experience).delete()
    db.query(Skill).delete()
    db.query(Profile).delete()
    db.commit()

    with patch("app.services.gemini.generate_structured", new_callable=AsyncMock, return_value=mock_structured), \
         patch("app.services.gemini.embed_text", new_callable=AsyncMock, return_value=[0.1] * 3072), \
         patch("app.services.qdrant_store.upsert_embedding"):
        from app.services.profile_builder import build_profile
        profile = await build_profile(db, "Test resume text for a Python engineer")

        assert profile.name == "Test User"
        assert profile.email == "test@example.com"
        assert len(profile.skills) == 1
        assert profile.skills[0].name == "Python"
