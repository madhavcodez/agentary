"""Tests for the expert registry."""
import pytest

from app.services.crews.expert_registry import BUILTIN_EXPERTS


class TestBuiltinExperts:
    def test_eight_builtin_experts(self):
        assert len(BUILTIN_EXPERTS) == 8

    def test_all_experts_have_required_fields(self):
        required_fields = {"name", "slug", "description", "icon", "specialty", "tools", "system_prompt", "model_config_json"}
        for expert in BUILTIN_EXPERTS:
            missing = required_fields - set(expert.keys())
            assert not missing, f"Expert {expert.get('slug', '?')} missing fields: {missing}"

    def test_all_slugs_unique(self):
        slugs = [e["slug"] for e in BUILTIN_EXPERTS]
        assert len(slugs) == len(set(slugs)), "Duplicate slugs found"

    def test_system_prompts_300_plus_words(self):
        for expert in BUILTIN_EXPERTS:
            word_count = len(expert["system_prompt"].split())
            assert word_count >= 100, (
                f"Expert {expert['slug']} system prompt only has {word_count} words "
                f"(expected 100+)"
            )

    def test_expected_slugs(self):
        expected = {
            "web-researcher", "data-analyst", "voice-caller", "synthesizer",
            "report-writer", "market-analyst", "property-researcher", "local-scout",
        }
        actual = {e["slug"] for e in BUILTIN_EXPERTS}
        assert expected == actual

    def test_synthesizer_has_no_tools(self):
        synth = next(e for e in BUILTIN_EXPERTS if e["slug"] == "synthesizer")
        assert synth["tools"] == []

    def test_web_researcher_has_search_tools(self):
        wr = next(e for e in BUILTIN_EXPERTS if e["slug"] == "web-researcher")
        assert "gemini_search" in wr["tools"]
        assert "exa_search" in wr["tools"]
        assert "web_scraper" in wr["tools"]

    def test_all_experts_have_icon(self):
        for expert in BUILTIN_EXPERTS:
            assert expert.get("icon"), f"Expert {expert['slug']} has no icon"

    def test_all_experts_have_color(self):
        for expert in BUILTIN_EXPERTS:
            assert expert.get("color"), f"Expert {expert['slug']} has no color"
            assert expert["color"].startswith("#"), f"Expert {expert['slug']} color should be hex"
