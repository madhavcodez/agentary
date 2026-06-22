"""Tests for the voice extraction system.

Covers:
- TranscriptProcessor (sync, no DB)
- CallScriptGenerator (async, mock Gemini)
- ExtractionService helpers (sync/async, mock Gemini + DB)
- VoicePipelineAdapter (Twilio config check)
- Templates (lookup + validation)
- API routes (FastAPI TestClient)
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.models.finding import FindingType

# ---------------------------------------------------------------------------
# 1. TranscriptProcessor
# ---------------------------------------------------------------------------


class TestCleanTranscript:
    """Tests for _clean_transcript — filler word removal and cleanup."""

    def test_removes_filler_words(self):
        from app.services.voice.transcript_processor import _clean_transcript

        raw = "Agent: Um, so basically I was, uh, calling about the project."
        cleaned = _clean_transcript(raw)
        assert "um" not in cleaned.lower().split()
        assert "uh" not in cleaned.lower().split()
        assert "basically" not in cleaned.lower()
        # Core content survives
        assert "calling" in cleaned.lower()
        assert "project" in cleaned.lower()

    def test_removes_repeated_words(self):
        from app.services.voice.transcript_processor import _clean_transcript

        raw = "User: The the meeting is is tomorrow."
        cleaned = _clean_transcript(raw)
        # Should collapse "the the" -> "the" and "is is" -> "is"
        assert "the the" not in cleaned.lower()
        assert "is is" not in cleaned.lower()
        assert "meeting" in cleaned.lower()

    def test_removes_false_starts(self):
        from app.services.voice.transcript_processor import _clean_transcript

        raw = "Agent: I was go- I was going to say hello."
        cleaned = _clean_transcript(raw)
        assert "go-" not in cleaned
        assert "going to say hello" in cleaned.lower()

    def test_preserves_speaker_prefix(self):
        from app.services.voice.transcript_processor import _clean_transcript

        raw = "Agent: Hello there.\nUser: Hi, how are you?"
        cleaned = _clean_transcript(raw)
        assert cleaned.startswith("Agent:")
        assert "User:" in cleaned

    def test_empty_input(self):
        from app.services.voice.transcript_processor import _clean_transcript

        assert _clean_transcript("") == ""
        assert _clean_transcript("   \n\n  ") == ""

    def test_multiword_fillers_removed(self):
        from app.services.voice.transcript_processor import _clean_transcript

        raw = "Agent: You know, I mean, sort of like the kind of thing we discussed."
        cleaned = _clean_transcript(raw)
        assert "you know" not in cleaned.lower()
        assert "i mean" not in cleaned.lower()


class TestCalculateTalkRatio:
    """Tests for _calculate_talk_ratio with multi-speaker segments."""

    def test_two_speakers_ratio(self):
        from app.services.voice.transcript_processor import _calculate_talk_ratio

        segments = [
            {"speaker": "Agent", "text": "Hello how are you today", "word_count": 5},
            {"speaker": "User", "text": "Good thanks and you", "word_count": 4},
            {"speaker": "Agent", "text": "Great", "word_count": 1},
        ]
        ratio = _calculate_talk_ratio(segments)
        # Agent: 6 words, User: 4 words, total 10
        assert ratio["Agent"] == pytest.approx(0.6, abs=0.01)
        assert ratio["User"] == pytest.approx(0.4, abs=0.01)

    def test_agent_user_keywords_detected(self):
        from app.services.voice.transcript_processor import _calculate_talk_ratio

        segments = [
            {"speaker": "Agent", "text": "one two three", "word_count": 3},
            {"speaker": "Customer", "text": "four five", "word_count": 2},
        ]
        ratio = _calculate_talk_ratio(segments)
        assert "agent_ratio" in ratio
        assert "user_ratio" in ratio
        assert ratio["agent_ratio"] == pytest.approx(0.6, abs=0.01)
        assert ratio["user_ratio"] == pytest.approx(0.4, abs=0.01)

    def test_two_unknown_speakers_fallback(self):
        """When neither speaker matches agent/user keywords, first is agent."""
        from app.services.voice.transcript_processor import _calculate_talk_ratio

        segments = [
            {"speaker": "Alice", "text": "one two", "word_count": 2},
            {"speaker": "Bob", "text": "three four five", "word_count": 3},
        ]
        ratio = _calculate_talk_ratio(segments)
        assert "agent_ratio" in ratio
        assert "user_ratio" in ratio
        assert ratio["agent_ratio"] == pytest.approx(0.4, abs=0.01)
        assert ratio["user_ratio"] == pytest.approx(0.6, abs=0.01)

    def test_empty_segments(self):
        from app.services.voice.transcript_processor import _calculate_talk_ratio

        assert _calculate_talk_ratio([]) == {}

    def test_single_speaker(self):
        from app.services.voice.transcript_processor import _calculate_talk_ratio

        segments = [
            {"speaker": "Agent", "text": "hello world", "word_count": 2},
        ]
        ratio = _calculate_talk_ratio(segments)
        assert ratio["Agent"] == pytest.approx(1.0, abs=0.001)


class TestExtractKeyMoments:
    """Tests for _extract_key_moments — detecting questions, objections, agreements."""

    def test_detects_question(self):
        from app.services.voice.transcript_processor import _extract_key_moments

        transcript = "Agent: What time do you open?"
        moments = _extract_key_moments(transcript)
        types = [m["type"] for m in moments]
        assert "question" in types
        assert moments[0]["speaker"] == "Agent"

    def test_detects_objection(self):
        from app.services.voice.transcript_processor import _extract_key_moments

        transcript = "User: I don't think that would work for us honestly."
        moments = _extract_key_moments(transcript)
        types = [m["type"] for m in moments]
        assert "objection" in types

    def test_detects_agreement(self):
        from app.services.voice.transcript_processor import _extract_key_moments

        transcript = "User: Absolutely, that sounds good to me."
        moments = _extract_key_moments(transcript)
        types = [m["type"] for m in moments]
        assert "agreement" in types

    def test_detects_information_exchange(self):
        from app.services.voice.transcript_processor import _extract_key_moments

        transcript = "User: My name is John Smith and I work at Acme Corp."
        moments = _extract_key_moments(transcript)
        types = [m["type"] for m in moments]
        assert "information" in types

    def test_short_objection_ignored(self):
        """Objection needs at least 4 words to avoid false positives."""
        from app.services.voice.transcript_processor import _extract_key_moments

        transcript = "User: But no."
        moments = _extract_key_moments(transcript)
        types = [m["type"] for m in moments]
        assert "objection" not in types

    def test_multiple_moment_types_in_one_line(self):
        """A line can trigger both question and agreement, etc."""
        from app.services.voice.transcript_processor import _extract_key_moments

        transcript = "User: Sure, absolutely, but can we reschedule?"
        moments = _extract_key_moments(transcript)
        types = [m["type"] for m in moments]
        assert "question" in types
        assert "agreement" in types

    def test_empty_transcript_returns_no_moments(self):
        from app.services.voice.transcript_processor import _extract_key_moments

        assert _extract_key_moments("") == []
        assert _extract_key_moments("   \n\n  ") == []


class TestProcessTranscript:
    """Tests for the top-level process_transcript function."""

    def test_full_processing(self):
        from app.services.voice.transcript_processor import process_transcript

        raw = (
            "Agent: Um, hi there, is this John?\n"
            "User: Yeah, this is John.\n"
            "Agent: Great, uh, I had a quick question about your hours?\n"
            "User: Sure, we are open nine to five."
        )
        result = process_transcript(raw)

        assert result["cleaned_transcript"]  # non-empty
        assert result["word_count"] > 0
        assert isinstance(result["segments"], list)
        assert len(result["segments"]) == 4
        assert isinstance(result["talk_ratio"], dict)
        assert isinstance(result["key_moments"], list)

    def test_empty_transcript_returns_empty_result(self):
        from app.services.voice.transcript_processor import process_transcript

        result = process_transcript("")
        assert result["cleaned_transcript"] == ""
        assert result["segments"] == []
        assert result["talk_ratio"] == {}
        assert result["key_moments"] == []
        assert result["word_count"] == 0

    def test_whitespace_only_returns_empty_result(self):
        from app.services.voice.transcript_processor import process_transcript

        result = process_transcript("   \n\n   ")
        assert result["cleaned_transcript"] == ""
        assert result["word_count"] == 0

    def test_with_provided_segments(self):
        from app.services.voice.transcript_processor import process_transcript

        raw = "Agent: Hello\nUser: Hi"
        segments = [
            {"speaker": "Agent", "text": "Hello", "timestamp": 0.0},
            {"speaker": "User", "text": "Hi", "timestamp": 1.5},
        ]
        result = process_transcript(raw, segments=segments)
        assert len(result["segments"]) == 2
        assert result["segments"][0]["timestamp"] == 0.0
        assert result["segments"][1]["timestamp"] == 1.5


# ---------------------------------------------------------------------------
# 2. CallScriptGenerator
# ---------------------------------------------------------------------------


class TestGenerateScript:
    """Tests for generate_script — async, needs mock_gemini."""

    @pytest.mark.asyncio
    async def test_returns_valid_script_structure(self, mock_gemini):
        from app.services.voice.call_script_generator import generate_script

        # Mock generate_structured to return a minimal valid script
        with patch(
            "app.services.voice.call_script_generator.generate_structured",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = {
                "opener": "Hi, is this Jane?",
                "questions": [
                    {
                        "field": "business_hours",
                        "primary_question": "What are your hours?",
                        "follow_up": "And on weekends?",
                        "probes": ["Any holiday hours?"],
                    }
                ],
                "objection_handlers": {
                    "busy": "I can call back later.",
                },
                "closing": "Thanks for your time!",
                "voicemail_script": "Hi Jane, this is Alex.",
            }

            session_data = {
                "target_name": "Jane",
                "target_business": "Acme Corp",
                "extraction_goals": [
                    {"field": "business_hours", "question": "What are your hours?", "type": "text", "required": True},
                ],
                "session_type": "research_extraction",
            }
            result = await generate_script(session_data)

            assert "opener" in result
            assert "questions" in result
            assert "objection_handlers" in result
            assert "closing" in result
            assert "voicemail_script" in result
            assert isinstance(result["questions"], list)
            assert len(result["questions"]) >= 1

    @pytest.mark.asyncio
    async def test_fills_default_objection_handlers(self, mock_gemini):
        """Missing objection handlers in Gemini response get filled with defaults."""
        from app.services.voice.call_script_generator import generate_script

        with patch(
            "app.services.voice.call_script_generator.generate_structured",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = {
                "opener": "Hello!",
                "questions": [],
            }

            result = await generate_script({"target_name": "Test"})

            handlers = result["objection_handlers"]
            assert "busy" in handlers
            assert "not_interested" in handlers
            assert "who_are_you" in handlers

    @pytest.mark.asyncio
    async def test_uncovered_goals_get_fallback_questions(self, mock_gemini):
        """Extraction goals not covered by Gemini output get auto-generated questions."""
        from app.services.voice.call_script_generator import generate_script

        with patch(
            "app.services.voice.call_script_generator.generate_structured",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = {
                "opener": "Hi!",
                "questions": [],
                "objection_handlers": {},
                "closing": "Bye!",
                "voicemail_script": "Leave a message.",
            }

            session_data = {
                "target_name": "Bob",
                "extraction_goals": [
                    {"field": "pricing", "question": "How much?", "type": "currency", "required": True},
                    {"field": "hours", "question": "When open?", "type": "text", "required": False},
                ],
            }
            result = await generate_script(session_data)

            fields_covered = {q["field"] for q in result["questions"]}
            assert "pricing" in fields_covered
            assert "hours" in fields_covered


class TestBuildSystemPrompt:
    """Tests for build_system_prompt — async, pure string building."""

    @pytest.mark.asyncio
    async def test_includes_persona(self):
        from app.services.voice.call_script_generator import build_system_prompt

        session_data = {
            "target_name": "Alice",
            "persona_config": {
                "name": "Jordan",
                "role": "Researcher",
                "tone": "warm",
                "style": "casual",
            },
            "extraction_goals": [],
        }
        script = {"opener": "Hey!", "questions": [], "objection_handlers": {}}
        prompt = await build_system_prompt(session_data, script)

        assert "Jordan" in prompt
        assert "Researcher" in prompt
        assert "warm" in prompt

    @pytest.mark.asyncio
    async def test_includes_goals_and_context(self):
        from app.services.voice.call_script_generator import build_system_prompt

        session_data = {
            "target_name": "Dave",
            "target_business": "Widget Co",
            "target_context": {"industry": "manufacturing"},
            "extraction_goals": [
                {"field": "revenue", "question": "Annual revenue?", "type": "currency", "required": True},
            ],
        }
        script = {
            "opener": "Hi Dave!",
            "questions": [
                {"field": "revenue", "primary_question": "What's your annual revenue?"},
            ],
            "objection_handlers": {"busy": "I can call later."},
            "closing": "Thanks!",
        }
        prompt = await build_system_prompt(session_data, script)

        assert "Dave" in prompt
        assert "Widget Co" in prompt
        assert "manufacturing" in prompt
        assert "revenue" in prompt.lower()

    @pytest.mark.asyncio
    async def test_with_no_context_no_persona(self):
        """Handles missing optional fields gracefully."""
        from app.services.voice.call_script_generator import build_system_prompt

        session_data = {
            "target_name": "Someone",
        }
        script = {"opener": "Hello", "questions": [], "objection_handlers": {}}
        prompt = await build_system_prompt(session_data, script)

        # Should use default persona
        assert "Alex" in prompt
        assert "Research Associate" in prompt
        assert "Someone" in prompt

    @pytest.mark.asyncio
    async def test_prompt_contains_critical_rules(self):
        from app.services.voice.call_script_generator import build_system_prompt

        session_data = {"target_name": "Test"}
        script = {"opener": "Hi", "questions": [], "objection_handlers": {}}
        prompt = await build_system_prompt(session_data, script)

        assert "CRITICAL RULES" in prompt
        assert "Never break character" in prompt


# ---------------------------------------------------------------------------
# 3. ExtractionService helpers
# ---------------------------------------------------------------------------


class TestValidateExtraction:
    """Tests for _validate_extraction with various field types."""

    def test_string_field_accepts_string(self):
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "string"}
        assert _validate_extraction(field, "hello") is True

    def test_string_field_rejects_number(self):
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "string"}
        assert _validate_extraction(field, 42) is False

    def test_number_field_accepts_int_and_float(self):
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "number"}
        assert _validate_extraction(field, 42) is True
        assert _validate_extraction(field, 3.14) is True

    def test_number_field_accepts_numeric_string(self):
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "number"}
        assert _validate_extraction(field, "99.5") is True

    def test_number_field_rejects_non_numeric_string(self):
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "number"}
        assert _validate_extraction(field, "not a number") is False

    def test_boolean_field(self):
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "boolean"}
        assert _validate_extraction(field, True) is True
        assert _validate_extraction(field, False) is True
        assert _validate_extraction(field, "yes") is False

    def test_list_field(self):
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "list"}
        assert _validate_extraction(field, ["a", "b"]) is True
        assert _validate_extraction(field, "not a list") is False

    def test_enum_field_with_options(self):
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "enum", "options": ["positive", "neutral", "negative"]}
        assert _validate_extraction(field, "positive") is True
        assert _validate_extraction(field, "Positive") is True  # case-insensitive
        assert _validate_extraction(field, "angry") is False

    def test_currency_accepts_number_and_string(self):
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "currency"}
        assert _validate_extraction(field, 100) is True
        assert _validate_extraction(field, 49.99) is True
        assert _validate_extraction(field, "$100") is True

    def test_unknown_type_passes(self):
        """Fields with unrecognized types should pass validation (permissive)."""
        from app.services.voice.extraction_service import _validate_extraction

        field = {"type": "unknown_custom_type"}
        # No validator registered, so isinstance check is skipped
        assert _validate_extraction(field, "anything") is True


class TestFindGoalSpec:
    """Tests for _find_goal_spec with exact and case-insensitive matching."""

    def test_exact_match(self):
        from app.services.voice.extraction_service import _find_goal_spec

        goals = [
            {"name": "business_hours", "type": "text"},
            {"name": "address", "type": "text"},
        ]
        result = _find_goal_spec("business_hours", goals)
        assert result is not None
        assert result["name"] == "business_hours"

    def test_case_insensitive_match(self):
        from app.services.voice.extraction_service import _find_goal_spec

        goals = [
            {"name": "Business_Hours", "type": "text"},
        ]
        result = _find_goal_spec("business_hours", goals)
        assert result is not None
        assert result["name"] == "Business_Hours"

    def test_no_match_returns_none(self):
        from app.services.voice.extraction_service import _find_goal_spec

        goals = [{"name": "address", "type": "text"}]
        assert _find_goal_spec("nonexistent_field", goals) is None

    def test_field_name_key_fallback(self):
        """Goals using 'field_name' instead of 'name' should still match."""
        from app.services.voice.extraction_service import _find_goal_spec

        goals = [{"field_name": "email", "type": "email"}]
        result = _find_goal_spec("email", goals)
        assert result is not None

    def test_exact_match_preferred_over_case_insensitive(self):
        from app.services.voice.extraction_service import _find_goal_spec

        goals = [
            {"name": "Price", "type": "currency"},
            {"name": "price", "type": "currency"},
        ]
        # Exact match loop runs first, should get the exact one
        result = _find_goal_spec("price", goals)
        assert result is not None
        assert result["name"] == "price"


class TestComputeQualityScore:
    """Tests for _compute_quality_score with required/optional fields."""

    def test_all_required_fields_extracted(self):
        from app.services.voice.extraction_service import _compute_quality_score

        fields = [
            {"field_name": "hours", "value": "9-5", "confidence": 0.9},
            {"field_name": "address", "value": "123 Main St", "confidence": 0.8},
        ]
        goals = [
            {"name": "hours", "required": True},
            {"name": "address", "required": True},
        ]
        score = _compute_quality_score(fields, goals)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_partial_required_fields(self):
        from app.services.voice.extraction_service import _compute_quality_score

        fields = [
            {"field_name": "hours", "value": "9-5", "confidence": 0.9},
            {"field_name": "address", "value": None, "confidence": 0.0},
        ]
        goals = [
            {"name": "hours", "required": True},
            {"name": "address", "required": True},
        ]
        score = _compute_quality_score(fields, goals)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_no_required_fields_falls_back_to_all(self):
        """When no goals are marked required, all goals are treated as required."""
        from app.services.voice.extraction_service import _compute_quality_score

        fields = [
            {"field_name": "hours", "value": "9-5", "confidence": 0.8},
        ]
        goals = [
            {"name": "hours", "required": False},
            {"name": "website", "required": False},
        ]
        score = _compute_quality_score(fields, goals)
        assert score == pytest.approx(0.5, abs=0.01)

    def test_low_confidence_excluded(self):
        """Fields with confidence below _MIN_FINDING_CONFIDENCE are not counted."""
        from app.services.voice.extraction_service import _compute_quality_score

        fields = [
            {"field_name": "hours", "value": "9-5", "confidence": 0.1},
        ]
        goals = [
            {"name": "hours", "required": True},
        ]
        score = _compute_quality_score(fields, goals)
        assert score == pytest.approx(0.0, abs=0.01)

    def test_empty_goals(self):
        from app.services.voice.extraction_service import _compute_quality_score

        assert _compute_quality_score([], []) == 0.0


class TestFindingTypeForField:
    """Tests for _finding_type_for_field returning correct FindingType enums."""

    def test_price_keywords(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("regular_price") == FindingType.price
        assert _finding_type_for_field("total_cost") == FindingType.price
        assert _finding_type_for_field("annual_revenue") == FindingType.price
        assert _finding_type_for_field("salary_range") == FindingType.price
        assert _finding_type_for_field("budget") == FindingType.price

    def test_availability_keywords(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("next_available") == FindingType.availability
        assert _finding_type_for_field("availability_window") == FindingType.availability
        assert _finding_type_for_field("open_slots") == FindingType.availability

    def test_risk_keywords(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("risk_level") == FindingType.risk
        assert _finding_type_for_field("main_concern") == FindingType.risk
        assert _finding_type_for_field("known_issue") == FindingType.risk

    def test_opportunity_keywords(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("growth_opportunity") == FindingType.opportunity
        assert _finding_type_for_field("market_potential") == FindingType.opportunity

    def test_trend_keywords(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("industry_trend") == FindingType.trend
        assert _finding_type_for_field("pricing_pattern") == FindingType.trend
        assert _finding_type_for_field("recent_change") == FindingType.trend

    def test_quote_keywords(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("ceo_quote") == FindingType.quote
        assert _finding_type_for_field("what_they_said") == FindingType.quote
        assert _finding_type_for_field("mentioned_detail") == FindingType.quote

    def test_contact_info_keywords(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("contact_person") == FindingType.contact_info
        assert _finding_type_for_field("email_address") == FindingType.contact_info
        assert _finding_type_for_field("phone_number") == FindingType.contact_info

    def test_sentiment_keywords(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("customer_sentiment") == FindingType.sentiment
        assert _finding_type_for_field("overall_feeling") == FindingType.sentiment
        assert _finding_type_for_field("opinion_on_product") == FindingType.sentiment

    def test_statistic_keywords(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("employee_count") == FindingType.statistic
        assert _finding_type_for_field("total_number") == FindingType.statistic
        assert _finding_type_for_field("success_rate") == FindingType.statistic
        assert _finding_type_for_field("completion_percent") == FindingType.statistic

    def test_default_is_data_point(self):
        from app.services.voice.extraction_service import _finding_type_for_field

        assert _finding_type_for_field("business_hours") == FindingType.data_point
        assert _finding_type_for_field("services") == FindingType.data_point
        assert _finding_type_for_field("random_field") == FindingType.data_point


# ---------------------------------------------------------------------------
# 4. VoicePipelineAdapter
# ---------------------------------------------------------------------------


class TestIsTwilioConfigured:
    """Tests for is_twilio_configured — returns False when credentials missing."""

    def test_returns_false_with_no_credentials(self):
        with patch("app.services.voice.voice_pipeline_adapter.settings") as mock_settings:
            mock_settings.twilio_account_sid = ""
            mock_settings.twilio_auth_token = ""
            mock_settings.twilio_from_number = ""
            mock_settings.twilio_webhook_base_url = ""

            from app.services.voice.voice_pipeline_adapter import is_twilio_configured

            assert is_twilio_configured() is False

    def test_returns_false_with_partial_credentials(self):
        with patch("app.services.voice.voice_pipeline_adapter.settings") as mock_settings:
            mock_settings.twilio_account_sid = "AC123"
            mock_settings.twilio_auth_token = "token"
            mock_settings.twilio_from_number = ""
            mock_settings.twilio_webhook_base_url = ""

            from app.services.voice.voice_pipeline_adapter import is_twilio_configured

            assert is_twilio_configured() is False

    def test_returns_true_with_all_credentials(self):
        with patch("app.services.voice.voice_pipeline_adapter.settings") as mock_settings:
            mock_settings.twilio_account_sid = "AC123"
            mock_settings.twilio_auth_token = "token123"
            mock_settings.twilio_from_number = "+15551234567"
            mock_settings.twilio_webhook_base_url = "https://example.com"

            from app.services.voice.voice_pipeline_adapter import is_twilio_configured

            assert is_twilio_configured() is True


# ---------------------------------------------------------------------------
# 5. Templates
# ---------------------------------------------------------------------------


class TestListTemplates:
    """Tests for list_templates and template count."""

    def test_returns_six_templates(self):
        from app.services.voice.templates import list_templates

        templates = list_templates()
        assert len(templates) == 6

    def test_template_list_items_have_required_keys(self):
        from app.services.voice.templates import list_templates

        templates = list_templates()
        for t in templates:
            assert "name" in t
            assert "description" in t
            assert "category" in t
            assert "field_count" in t
            assert isinstance(t["field_count"], int)


class TestGetTemplateByName:
    """Tests for get_template_by_name with case-insensitive lookup."""

    def test_exact_name(self):
        from app.services.voice.templates import get_template_by_name

        template = get_template_by_name("Business Info")
        assert template is not None
        assert template["name"] == "Business Info"

    def test_case_insensitive(self):
        from app.services.voice.templates import get_template_by_name

        template = get_template_by_name("business info")
        assert template is not None
        assert template["name"] == "Business Info"

    def test_uppercase(self):
        from app.services.voice.templates import get_template_by_name

        template = get_template_by_name("PRICING")
        assert template is not None
        assert template["name"] == "Pricing"

    def test_nonexistent_returns_none(self):
        from app.services.voice.templates import get_template_by_name

        assert get_template_by_name("Nonexistent Template") is None

    def test_returns_copy(self):
        """Returned template should be a copy, not a reference to the original."""
        from app.services.voice.templates import get_template_by_name

        t1 = get_template_by_name("Custom")
        t2 = get_template_by_name("Custom")
        assert t1 is not t2


class TestGetTemplateByCategory:
    """Tests for get_template_by_category."""

    def test_business_info_category(self):
        from app.services.voice.templates import get_template_by_category

        template = get_template_by_category("business_info")
        assert template is not None
        assert template["category"] == "business_info"
        assert template["name"] == "Business Info"

    def test_pricing_category(self):
        from app.services.voice.templates import get_template_by_category

        template = get_template_by_category("pricing")
        assert template is not None
        assert template["name"] == "Pricing"

    def test_nonexistent_category_returns_none(self):
        from app.services.voice.templates import get_template_by_category

        assert get_template_by_category("nonexistent") is None


class TestTemplateSchemaValidity:
    """All built-in templates must have a valid extraction_schema structure."""

    def test_all_templates_have_extraction_schema(self):
        from app.services.voice.templates import BUILT_IN_TEMPLATES

        for template in BUILT_IN_TEMPLATES:
            assert "extraction_schema" in template, (
                f"Template '{template['name']}' missing extraction_schema"
            )
            schema = template["extraction_schema"]
            assert "fields" in schema, (
                f"Template '{template['name']}' schema missing 'fields' key"
            )
            assert isinstance(schema["fields"], list), (
                f"Template '{template['name']}' fields should be a list"
            )

    def test_all_fields_have_required_keys(self):
        from app.services.voice.templates import BUILT_IN_TEMPLATES

        for template in BUILT_IN_TEMPLATES:
            for field in template["extraction_schema"]["fields"]:
                assert "name" in field, (
                    f"Field in '{template['name']}' missing 'name'"
                )
                assert "type" in field, (
                    f"Field '{field.get('name', '?')}' in '{template['name']}' missing 'type'"
                )
                assert "question" in field, (
                    f"Field '{field['name']}' in '{template['name']}' missing 'question'"
                )
                assert "required" in field, (
                    f"Field '{field['name']}' in '{template['name']}' missing 'required'"
                )
                assert isinstance(field["required"], bool), (
                    f"Field '{field['name']}' in '{template['name']}' 'required' should be bool"
                )

    def test_all_templates_have_persona(self):
        from app.services.voice.templates import BUILT_IN_TEMPLATES

        for template in BUILT_IN_TEMPLATES:
            assert "persona" in template, (
                f"Template '{template['name']}' missing persona"
            )
            persona = template["persona"]
            assert "name" in persona
            assert "role" in persona
            assert "tone" in persona
            assert "style" in persona

    def test_all_templates_have_name_description_category(self):
        from app.services.voice.templates import BUILT_IN_TEMPLATES

        for template in BUILT_IN_TEMPLATES:
            assert template.get("name"), "Template missing name"
            assert template.get("description"), (
                f"Template '{template['name']}' missing description"
            )
            assert template.get("category"), (
                f"Template '{template['name']}' missing category"
            )

    def test_template_names_are_unique(self):
        from app.services.voice.templates import BUILT_IN_TEMPLATES

        names = [t["name"] for t in BUILT_IN_TEMPLATES]
        assert len(names) == len(set(names)), "Duplicate template names found"

    def test_template_categories_are_unique(self):
        from app.services.voice.templates import BUILT_IN_TEMPLATES

        categories = [t["category"] for t in BUILT_IN_TEMPLATES]
        assert len(categories) == len(set(categories)), "Duplicate template categories found"


# ---------------------------------------------------------------------------
# 6. API Routes
# ---------------------------------------------------------------------------


class TestVoiceTemplateRoutes:
    """Tests for /voice/templates API endpoints using FastAPI TestClient."""

    def test_get_all_templates(self, client):
        response = client.get("/voice/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) == 6

    def test_get_template_by_name(self, client):
        response = client.get("/voice/templates/Business%20Info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Business Info"
        assert "extraction_schema" in data
        assert "fields" in data["extraction_schema"]

    def test_get_template_nonexistent_returns_404(self, client):
        response = client.get("/voice/templates/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_pricing_template(self, client):
        response = client.get("/voice/templates/Pricing")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Pricing"
        assert data["category"] == "pricing"

    def test_template_list_item_shape(self, client):
        response = client.get("/voice/templates")
        assert response.status_code == 200
        item = response.json()["templates"][0]
        assert "name" in item
        assert "description" in item
        assert "category" in item
        assert "field_count" in item
