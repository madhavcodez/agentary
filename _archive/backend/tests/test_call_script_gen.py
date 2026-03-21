from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_campaign():
    """Create a mock CallCampaign with related objects."""
    campaign = MagicMock()
    campaign.id = uuid.uuid4()
    campaign.match_id = uuid.uuid4()
    campaign.contact_id = uuid.uuid4()

    contact = MagicMock()
    contact.name = "Jane Smith"
    contact.title = "Engineering Manager"
    contact.company = "Acme Corp"
    contact.phone = "+15551234567"
    campaign.contact = contact

    match = MagicMock()
    match.id = campaign.match_id
    match.opportunity_id = uuid.uuid4()
    match.profile_id = uuid.uuid4()
    match.composite_score = 0.85

    opportunity = MagicMock()
    opportunity.id = match.opportunity_id
    opportunity.company = "Acme Corp"
    opportunity.title = "ML Engineer"
    opportunity.description = "We are looking for an ML engineer with experience in LLMs."

    profile = MagicMock()
    profile.id = match.profile_id
    profile.name = "Madhav Chauhan"
    profile.summary = "AI/ML engineer and full-stack developer"

    dossier = MagicMock()
    dossier.match_id = match.id
    dossier.content_md = "## Company Overview\nAcme Corp is a leading AI company."

    return campaign, match, opportunity, profile, dossier


class TestGenerateCallScript:
    @pytest.mark.asyncio
    async def test_script_structure(self):
        """Verify the generated script has all required keys."""
        campaign, match, opportunity, profile, dossier = _make_campaign()

        mock_db = MagicMock()
        # Set up query chains for each model lookup
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            match,        # Match lookup
            opportunity,  # Opportunity lookup
            profile,      # Profile lookup
            dossier,      # Dossier lookup
        ]

        gemini_output = {
            "opener": "Hi, this is SecretAIRY calling on behalf of Madhav Chauhan about the ML Engineer role.",
            "gatekeeper_script": "I'm calling about a specific engineering position.",
            "pitch_points": [
                "Strong LLM experience",
                "Full-stack development skills",
                "Relevant ML pipeline work",
            ],
            "voicemail_script": "Hi, this is a message on behalf of Madhav Chauhan.",
            "scheduling_prompts": [
                "Would Tuesday or Wednesday work?",
                "What time suits you best?",
            ],
            "callback_number": "+15551234567",
        }

        with patch(
            "app.services.call_script_gen.gemini.generate_structured",
            new_callable=AsyncMock,
            return_value=gemini_output,
        ):
            from app.services.call_script_gen import generate_call_script

            result = await generate_call_script(mock_db, campaign)

        assert "opener" in result
        assert "gatekeeper_script" in result
        assert "pitch_points" in result
        assert isinstance(result["pitch_points"], list)
        assert len(result["pitch_points"]) >= 1
        assert "voicemail_script" in result
        assert "scheduling_prompts" in result
        assert "callback_number" in result

    @pytest.mark.asyncio
    async def test_defaults_applied_on_missing_keys(self):
        """Verify defaults are applied when Gemini returns incomplete data."""
        campaign, match, opportunity, profile, dossier = _make_campaign()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            match,
            opportunity,
            profile,
            dossier,
        ]

        # Gemini returns partial response
        gemini_output = {
            "opener": "Hi there.",
        }

        with patch(
            "app.services.call_script_gen.gemini.generate_structured",
            new_callable=AsyncMock,
            return_value=gemini_output,
        ):
            from app.services.call_script_gen import generate_call_script

            result = await generate_call_script(mock_db, campaign)

        assert result["opener"] == "Hi there."
        # Defaults should fill in missing keys
        assert "gatekeeper_script" in result and result["gatekeeper_script"]
        assert "pitch_points" in result and len(result["pitch_points"]) >= 1
        assert "voicemail_script" in result and result["voicemail_script"]
        assert "scheduling_prompts" in result
        assert "callback_number" in result

    @pytest.mark.asyncio
    async def test_match_not_found(self):
        """Verify ValueError is raised when match does not exist."""
        campaign = MagicMock()
        campaign.match_id = uuid.uuid4()

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        from app.services.call_script_gen import generate_call_script

        with pytest.raises(ValueError, match="not found"):
            await generate_call_script(mock_db, campaign)
