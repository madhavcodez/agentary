"""Unit tests for the voice-driven quote caller."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.contractors.discovery import ContractorCandidate
from app.services.contractors.quote_caller import (
    PoolSpecs,
    QuoteResult,
    build_disclosure_preamble,
    build_quote_script,
    build_quote_system_prompt,
    parse_eta_weeks,
    parse_price_range,
    request_quote_via_voice,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _sample_contractor(phone: str = "+1-214-555-0101") -> ContractorCandidate:
    return ContractorCandidate(
        name="BlueWave Pools",
        phone=phone,
        address="100 Main St, Plano, TX 75023",
        rating=4.7,
        reviews_count=120,
        source="yelp",
        business_url="https://yelp.com/bluewave",
        raw_payload={},
    )


def _sample_specs() -> PoolSpecs:
    return PoolSpecs(
        shape="rectangular",
        width_ft=20.0,
        length_ft=40.0,
        depth_ft=6.0,
        backyard_sqft=1200.0,
    )


class _Listing:
    address = "123 Yard Lane, Plano, TX 75023"


# ---------------------------------------------------------------------------
# Prompt + disclosure
# ---------------------------------------------------------------------------


def test_disclosure_preamble_contains_tcpa_language() -> None:
    disclosure = build_disclosure_preamble()
    assert "automated" in disclosure.lower()
    assert "homebuyer" in disclosure.lower()
    assert "behalf of" in disclosure.lower()


def test_quote_script_mentions_specs_and_address() -> None:
    script = build_quote_script(
        "123 Yard Lane", _sample_specs(), city="Plano", state="TX"
    )
    assert "Plano TX" in script
    assert "20" in script and "40" in script
    assert "6 ft deep" in script


def test_quote_system_prompt_starts_with_disclosure() -> None:
    prompt = build_quote_system_prompt(
        contractor=_sample_contractor(),
        listing_address="123 Yard Lane",
        pool_specs=_sample_specs(),
    )
    disclosure = build_disclosure_preamble()
    # The disclosure MUST appear verbatim inside the OPENER block.
    assert disclosure in prompt
    # And it must precede the BODY.
    assert prompt.index("OPENER") < prompt.index("BODY")
    # And rule #1 must enforce it.
    assert "first sentence" in prompt.lower() or "never skip" in prompt.lower()


# ---------------------------------------------------------------------------
# PoolSpecs factory
# ---------------------------------------------------------------------------


def test_pool_specs_from_placement() -> None:
    placement = {"width_ft": 18.0, "length_ft": 36.0}
    specs = PoolSpecs.from_placement(
        placement, backyard_sqft=900.0, shape="kidney", depth_ft=5.5
    )
    assert specs.width_ft == 18.0
    assert specs.length_ft == 36.0
    assert specs.shape == "kidney"
    assert specs.depth_ft == 5.5
    assert specs.backyard_sqft == 900.0


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------


def test_parse_price_range_extracts_two_amounts() -> None:
    transcript = (
        "Agent: What's the ballpark?\n"
        "User: Usually between $65,000 and $85,000 depending on finishes.\n"
    )
    low, high = parse_price_range(transcript)
    assert low == 65_000.0
    assert high == 85_000.0


def test_parse_price_range_handles_k_suffix() -> None:
    low, high = parse_price_range("We're talking $70k to $90k typically.")
    assert low == 70_000.0
    assert high == 90_000.0


def test_parse_price_range_ignores_small_amounts() -> None:
    # $50 filing fee shouldn't be read as a pool quote.
    low, high = parse_price_range("Permit fee is $50, pool around $70,000.")
    assert low == 70_000.0
    assert high == 70_000.0


def test_parse_price_range_empty() -> None:
    assert parse_price_range("") == (None, None)
    assert parse_price_range(None) == (None, None)


def test_parse_eta_weeks_handles_week_range() -> None:
    assert parse_eta_weeks("Install is 8 to 12 weeks typically.") == 10


def test_parse_eta_weeks_handles_single_value() -> None:
    assert parse_eta_weeks("About 14 weeks from permit.") == 14


def test_parse_eta_weeks_converts_months() -> None:
    assert parse_eta_weeks("3 months turnaround") == pytest.approx(13, abs=1)


def test_parse_eta_weeks_missing() -> None:
    assert parse_eta_weeks("") is None
    assert parse_eta_weeks("We'll get back to you.") is None


# ---------------------------------------------------------------------------
# request_quote_via_voice — full happy path with pipeline mock
# ---------------------------------------------------------------------------


def _make_pipeline(
    *,
    status: str = "completed",
    transcript: str | None = None,
    recording_url: str | None = None,
    sid: str = "SIM_ABC",
) -> MagicMock:
    """Build a mock pipeline adapter matching the _VoicePipeline protocol."""
    pipeline = MagicMock()
    pipeline.build_gemini_live_config = MagicMock(
        return_value={
            "system_prompt": "placeholder — will be overridden",
            "voice_name": "Kore",
        }
    )

    async def _create(call_record, voice_extraction, db):
        if transcript is not None:
            call_record.transcript = transcript
        if recording_url is not None:
            call_record.recording_url = recording_url
        return {"status": status, "call_sid": sid}

    pipeline.create_outbound_call = AsyncMock(side_effect=_create)
    return pipeline


@pytest.mark.asyncio
async def test_request_quote_places_call_with_contractor_phone() -> None:
    pipeline = _make_pipeline(
        transcript=(
            "Agent: Ballpark?\n"
            "User: Around $65,000 to $80,000, about 10 weeks to install.\n"
        ),
    )
    contractor = _sample_contractor(phone="+1-214-555-0101")

    result = await request_quote_via_voice(
        contractor=contractor,
        listing=_Listing(),
        pool_specs=_sample_specs(),
        pipeline=pipeline,
    )

    # create_outbound_call was awaited with our phone number.
    pipeline.create_outbound_call.assert_awaited_once()
    _, kwargs = pipeline.create_outbound_call.call_args
    call_record = kwargs["call_record"]
    assert call_record.phone_number == "+1-214-555-0101"
    assert call_record.target_name == "BlueWave Pools"

    # Gemini Live config was requested AND overridden with TCPA prompt.
    pipeline.build_gemini_live_config.assert_called_once()
    live_cfg = pipeline.build_gemini_live_config.return_value
    assert build_disclosure_preamble() in live_cfg["system_prompt"]

    # Parsed result.
    assert result.status == "ok"
    assert result.price_low_usd == 65_000.0
    assert result.price_high_usd == 80_000.0
    assert result.eta_weeks == 10
    assert result.contractor_phone == "+1-214-555-0101"
    assert result.rating == 4.7


@pytest.mark.asyncio
async def test_request_quote_without_phone_returns_failed() -> None:
    pipeline = _make_pipeline()
    contractor = _sample_contractor(phone="")
    result = await request_quote_via_voice(
        contractor=contractor,
        listing=_Listing(),
        pool_specs=_sample_specs(),
        pipeline=pipeline,
    )
    assert result.status == "call_failed"
    pipeline.create_outbound_call.assert_not_called()


@pytest.mark.asyncio
async def test_request_quote_handles_declined() -> None:
    pipeline = _make_pipeline(status="declined", transcript=None)
    result = await request_quote_via_voice(
        contractor=_sample_contractor(),
        listing=_Listing(),
        pool_specs=_sample_specs(),
        pipeline=pipeline,
    )
    assert result.status == "declined"


@pytest.mark.asyncio
async def test_request_quote_propagates_adapter_exception_as_failed() -> None:
    """Security audit #4: ``notes`` must be an opaque label — the raw
    exception text is kept server-side (logged) but never surfaced in
    the API response, so callers cannot enumerate internal errors.
    """
    pipeline = MagicMock()
    pipeline.build_gemini_live_config = MagicMock(
        return_value={"system_prompt": "x"}
    )
    pipeline.create_outbound_call = AsyncMock(
        side_effect=RuntimeError("twilio exploded")
    )
    result = await request_quote_via_voice(
        contractor=_sample_contractor(),
        listing=_Listing(),
        pool_specs=_sample_specs(),
        pipeline=pipeline,
    )
    assert result.status == "call_failed"
    # Opaque label only; raw exception text must NOT leak.
    assert result.notes == "call_failed"
    assert "twilio exploded" not in (result.notes or "")


@pytest.mark.asyncio
async def test_request_quote_with_completed_but_unparseable_transcript() -> None:
    pipeline = _make_pipeline(
        transcript="Agent: Hi. User: Hi. Agent: Bye. User: Bye."
    )
    result = await request_quote_via_voice(
        contractor=_sample_contractor(),
        listing=_Listing(),
        pool_specs=_sample_specs(),
        pipeline=pipeline,
    )
    assert result.status == "parse_failed"


# ---------------------------------------------------------------------------
# QuoteResult serialization
# ---------------------------------------------------------------------------


def test_quote_result_to_jsonable_round_trip() -> None:
    q = QuoteResult(
        contractor_name="X",
        contractor_phone="555",
        status="ok",
        price_low_usd=70_000.0,
        price_high_usd=90_000.0,
        eta_weeks=10,
        rating=4.5,
    )
    payload = q.to_jsonable()
    assert payload["status"] == "ok"
    assert payload["price_low_usd"] == 70_000.0
    assert payload["eta_weeks"] == 10
