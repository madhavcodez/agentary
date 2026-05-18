"""Tests for the unified provider adapter layer.

Verifies that:
- ``ExaProvider`` translates SDK results into typed ``ExaSearchResult``
- Missing API keys surface as ``ExaUnavailable`` / ``GeminiUnavailable``
- The legacy ``services.gemini`` shim still resolves to the provider
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def test_exa_provider_translates_sdk_results(monkeypatch):
    from app.platform.infrastructure.providers import exa_provider
    from app.platform.infrastructure.providers.exa import ExaSearchResult

    # Pretend the SDK returns one result with the fields we read
    fake_response = SimpleNamespace(
        results=[
            SimpleNamespace(
                url="https://example.com/a",
                title="Example A",
                text="snippet body" * 10,
                score=0.87,
                published_date="2026-01-01",
            )
        ]
    )

    monkeypatch.setattr(exa_provider, "_client", MagicMock())
    exa_provider._client.search_and_contents.return_value = fake_response
    monkeypatch.setattr(
        "app.platform.infrastructure.providers.exa.settings.exa_api_key",
        "test-key",
        raising=False,
    )

    results = asyncio.run(exa_provider.search("anything", num_results=1))
    assert isinstance(results, list) and len(results) == 1
    assert isinstance(results[0], ExaSearchResult)
    assert results[0].url == "https://example.com/a"
    assert results[0].title == "Example A"
    assert results[0].snippet.startswith("snippet body")
    assert results[0].score == 0.87


def test_exa_provider_raises_when_unconfigured(monkeypatch):
    from app.platform.infrastructure.providers import exa_provider
    from app.platform.infrastructure.providers.exa import ExaUnavailable

    monkeypatch.setattr(exa_provider, "_client", None)
    monkeypatch.setattr(
        "app.platform.infrastructure.providers.exa.settings.exa_api_key",
        "",
        raising=False,
    )

    with pytest.raises(ExaUnavailable):
        asyncio.run(exa_provider.search("anything"))


def test_gemini_legacy_shim_routes_to_provider(monkeypatch):
    """``services.gemini.generate_text`` must still resolve to provider."""
    from app.services import gemini as legacy

    async def fake_generate_text(prompt, *, system="", model="x", temperature=0.7):
        return f"echo:{prompt}:{system}:{model}"

    with patch(
        "app.platform.infrastructure.providers.gemini.gemini_provider.generate_text",
        side_effect=fake_generate_text,
    ):
        out = asyncio.run(legacy.generate_text("hi", system="be terse"))
        assert out.startswith("echo:hi:be terse:")


def test_gemini_provider_parses_fenced_json(monkeypatch):
    """The JSON parser handles ``` ```json {...} ``` ``` fenced responses."""
    from app.platform.infrastructure.providers.gemini import _parse_json_strict_or_loose

    fenced = '```json\n{"key": "value", "n": 3}\n```'
    parsed = _parse_json_strict_or_loose(fenced)
    assert parsed == {"key": "value", "n": 3}


def test_gemini_provider_extracts_json_from_prose():
    """If Gemini emits prose before/after JSON, extract the brace block."""
    from app.platform.infrastructure.providers.gemini import _parse_json_strict_or_loose

    prose = 'Here is the answer:\n{"ok": true}\nLet me know if you need more.'
    parsed = _parse_json_strict_or_loose(prose)
    assert parsed == {"ok": True}
