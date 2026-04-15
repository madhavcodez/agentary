"""Voice-driven quote orchestration for pool contractors.

Wraps the existing Pipecat + Twilio + Gemini Live pipeline
(:mod:`app.services.voice.voice_pipeline_adapter`) to place TCPA-compliant
outbound calls that ask a contractor for a rough ballpark quote.

The *very first* thing the assistant says is an automated-call
disclosure (see :func:`build_disclosure_preamble`). This is baked into
the system prompt builder so it cannot be skipped.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Protocol

from ...models.voice_extraction import (
    CallDirection,
    CallRecord,
    CallStatus,
    VoiceExtraction,
)
from .discovery import ContractorCandidate

logger = logging.getLogger(__name__)

QuoteStatus = Literal[
    "ok",
    "declined",
    "no_answer",
    "hangup_before_disclosure",
    "call_failed",
    "not_configured",
    "parse_failed",
]


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PoolSpecs:
    """Physical spec used to describe the prospective pool on the call.

    Built from the output of
    :func:`app.verticals.pool_concierge.pool_placement.find_largest_pool_rectangle`
    plus a buyer-supplied shape/depth preference.
    """

    shape: str
    width_ft: float
    length_ft: float
    depth_ft: float
    backyard_sqft: float

    @classmethod
    def from_placement(
        cls,
        placement: dict[str, Any],
        *,
        shape: str = "rectangular",
        depth_ft: float = 6.0,
        backyard_sqft: float = 0.0,
    ) -> "PoolSpecs":
        """Build a :class:`PoolSpecs` from a placement dict.

        ``placement`` is the dict returned by
        :func:`find_largest_pool_rectangle` (keys ``width_ft``,
        ``length_ft``, ...).
        """
        width = float(placement.get("width_ft") or 0.0)
        length = float(placement.get("length_ft") or 0.0)
        return cls(
            shape=shape,
            width_ft=width,
            length_ft=length,
            depth_ft=float(depth_ft),
            backyard_sqft=float(backyard_sqft),
        )


@dataclass(frozen=True)
class QuoteResult:
    """Outcome of a single voice quote-request call."""

    contractor_name: str
    contractor_phone: str
    status: QuoteStatus
    price_low_usd: float | None = None
    price_high_usd: float | None = None
    eta_weeks: int | None = None
    transcript_url: str | None = None
    recording_url: str | None = None
    provider_call_id: str | None = None
    rating: float | None = None
    notes: str | None = None
    raw_transcript: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        """Return a JSON-safe representation (for JSONB persistence)."""
        return {
            "contractor_name": self.contractor_name,
            "contractor_phone": self.contractor_phone,
            "status": self.status,
            "price_low_usd": self.price_low_usd,
            "price_high_usd": self.price_high_usd,
            "eta_weeks": self.eta_weeks,
            "transcript_url": self.transcript_url,
            "recording_url": self.recording_url,
            "provider_call_id": self.provider_call_id,
            "rating": self.rating,
            "notes": self.notes,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Script + prompt builders
# ---------------------------------------------------------------------------


_TCPA_DISCLOSURE = (
    "Hello, this is an automated assistant calling on behalf of a "
    "prospective homebuyer interested in installing a pool. Do you have "
    "a moment for a brief inquiry? Press 1 to continue or hang up to "
    "decline."
)


def build_disclosure_preamble() -> str:
    """Return the exact TCPA disclosure sentence(s).

    Kept as a dedicated function so tests can assert its contents and
    so other callers (e.g. analytics) can match on it verbatim.
    """
    return _TCPA_DISCLOSURE


def build_quote_script(
    listing_address: str,
    pool_specs: PoolSpecs,
    city: str = "Plano",
    state: str = "TX",
) -> str:
    """Compose the body script the assistant reads after the disclosure."""
    return (
        f"I'm representing a buyer looking at a property at "
        f"{listing_address} in {city} {state}. They want a "
        f"{pool_specs.shape} pool roughly "
        f"{pool_specs.width_ft:.0f}\u00d7{pool_specs.length_ft:.0f} ft, "
        f"{pool_specs.depth_ft:.0f} ft deep. The backyard is about "
        f"{pool_specs.backyard_sqft:.0f} sqft. Could you give a rough "
        "ballpark quote and your typical install timeline?"
    )


def build_quote_system_prompt(
    contractor: ContractorCandidate,
    listing_address: str,
    pool_specs: PoolSpecs,
) -> str:
    """System prompt for Gemini Live during the quote call.

    The disclosure **must** be the first thing the assistant says
    before any other content, to satisfy TCPA. That requirement is
    encoded both in the ``OPENER`` line and explicitly as the first
    RULE so the model cannot re-order.
    """
    disclosure = build_disclosure_preamble()
    body = build_quote_script(listing_address, pool_specs)
    return (
        "You are an automated voice assistant placing an outbound call on "
        "behalf of a prospective homebuyer to request a rough ballpark "
        f"pool-installation quote from {contractor.name}.\n\n"
        f"OPENER (say this VERBATIM, before anything else):\n{disclosure}\n\n"
        "If the contractor indicates they do not consent or hangs up, "
        'end the call politely with "Thank you for your time." and do '
        "not continue.\n\n"
        f"BODY (after consent is given):\n{body}\n\n"
        "GOAL: capture (a) a rough price range in US dollars, (b) a "
        "typical install timeline in weeks. Ask at most one clarifying "
        "follow-up per item. Do not pressure for specifics.\n\n"
        "RULES:\n"
        "1. The very first sentence MUST be the OPENER above, verbatim. "
        "Never skip the automated-call disclosure.\n"
        "2. Never claim to be a human. If asked, confirm you are an "
        "automated assistant.\n"
        "3. Keep the conversation under 4 minutes.\n"
        "4. Do not share any personal information about the buyer.\n"
        "5. Thank the contractor and end gracefully once you have the "
        "ballpark or they decline."
    )


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------


_DOLLAR_PATTERN = re.compile(
    r"\$\s*([0-9]{1,3}(?:[,.][0-9]{3})*(?:\.[0-9]+)?)(\s*k)?",
    re.IGNORECASE,
)
_WEEK_PATTERN = re.compile(
    r"(\d{1,2})(?:\s*(?:to|[-\u2013])\s*(\d{1,2}))?\s*weeks?",
    re.IGNORECASE,
)
_MONTH_PATTERN = re.compile(
    r"(\d{1,2})(?:\s*(?:to|[-\u2013])\s*(\d{1,2}))?\s*months?",
    re.IGNORECASE,
)


def _parse_dollar_amount(token: str, has_k: bool) -> float:
    raw = token.replace(",", "").replace(" ", "")
    value = float(raw)
    if has_k:
        value *= 1_000.0
    return value


def parse_price_range(
    transcript: str | None,
) -> tuple[float | None, float | None]:
    """Extract a ``(low, high)`` USD price range from a transcript.

    Heuristic:
      * collect all dollar amounts
      * amounts >= $5,000 are treated as potential quotes (filters out
        small dollar figures mentioned incidentally)
      * if 2+ qualifying amounts exist, return ``(min, max)``
      * if exactly 1 exists, return ``(amount, amount)``
      * otherwise ``(None, None)``
    """
    if not transcript:
        return (None, None)
    amounts: list[float] = []
    for token, k_suffix in _DOLLAR_PATTERN.findall(transcript):
        try:
            amount = _parse_dollar_amount(token, bool(k_suffix))
        except ValueError:
            continue
        if amount >= 5_000.0:
            amounts.append(amount)
    if not amounts:
        return (None, None)
    if len(amounts) == 1:
        return (amounts[0], amounts[0])
    return (min(amounts), max(amounts))


def parse_eta_weeks(transcript: str | None) -> int | None:
    """Extract an install timeline in weeks from a transcript."""
    if not transcript:
        return None
    week_match = _WEEK_PATTERN.search(transcript)
    if week_match:
        low = int(week_match.group(1))
        high_raw = week_match.group(2)
        if high_raw:
            return (low + int(high_raw)) // 2
        return low
    month_match = _MONTH_PATTERN.search(transcript)
    if month_match:
        low = int(month_match.group(1))
        high_raw = month_match.group(2)
        if high_raw:
            months = (low + int(high_raw)) / 2
        else:
            months = float(low)
        return max(1, int(round(months * 4.345)))
    return None


# ---------------------------------------------------------------------------
# Call orchestration
# ---------------------------------------------------------------------------


class _VoicePipeline(Protocol):
    """Protocol the callable layer needs from the voice adapter.

    Exists so tests can inject a stub without monkey-patching modules.
    """

    async def create_outbound_call(
        self,
        call_record: CallRecord,
        voice_extraction: VoiceExtraction,
        db: Any,
    ) -> dict[str, Any]: ...

    def build_gemini_live_config(
        self,
        call_record: CallRecord,
        voice_extraction: VoiceExtraction,
    ) -> dict[str, Any]: ...


def _default_pipeline() -> _VoicePipeline:
    """Lazy import so the module doesn't pull Twilio at import time."""
    from ..voice import voice_pipeline_adapter  # type: ignore

    return voice_pipeline_adapter  # type: ignore[return-value]


def _build_voice_extraction_shell(
    contractor: ContractorCandidate,
    listing_address: str,
    pool_specs: PoolSpecs,
    max_call_duration_sec: int,
) -> VoiceExtraction:
    """Build an **unpersisted** ``VoiceExtraction`` used only as a carrier.

    The existing Pipecat adapter expects a ``VoiceExtraction`` row for
    persona/schema/script. Stream C doesn't want to pollute the
    extractions table for every quote call, so we assemble a lightweight
    in-memory shell and pass it straight through — no flush/commit.
    """
    system_prompt = build_quote_system_prompt(
        contractor=contractor,
        listing_address=listing_address,
        pool_specs=pool_specs,
    )
    script_body = build_quote_script(listing_address, pool_specs)

    extraction = VoiceExtraction()
    extraction.id = uuid.uuid4()
    extraction.name = f"pool_quote::{contractor.name}"
    extraction.description = (
        "Outbound pool-installation quote request (Stream C)."
    )
    extraction.objective = (
        "Collect a rough ballpark price range (USD) and typical install "
        "timeline (weeks) from the contractor."
    )
    extraction.persona = {
        "name": "Avery",
        "role": "Automated homebuyer assistant",
        "tone": "brief, polite, transparent about being automated",
        "system_prompt": system_prompt,
    }
    extraction.extraction_schema = {
        "fields": [
            {
                "name": "price_low_usd",
                "type": "number",
                "question": "What's the low end of your ballpark quote?",
                "required": True,
            },
            {
                "name": "price_high_usd",
                "type": "number",
                "question": "What's the high end of your ballpark quote?",
                "required": True,
            },
            {
                "name": "eta_weeks",
                "type": "number",
                "question": "What's your typical install timeline in weeks?",
                "required": True,
            },
        ]
    }
    extraction.call_script_template = (
        f"{build_disclosure_preamble()}\n\n{script_body}"
    )
    extraction.objection_handlers = [
        {
            "objection": "not interested",
            "response": "Understood — thank you for your time.",
        },
        {
            "objection": "are you a robot",
            "response": (
                "Yes, I'm an automated assistant placing this call on "
                "behalf of a homebuyer."
            ),
        },
    ]
    extraction.max_call_duration_seconds = int(max_call_duration_sec)
    return extraction


def _build_call_record_shell(
    contractor: ContractorCandidate,
    listing_address: str,
    voice_extraction_id: uuid.UUID,
) -> CallRecord:
    """Build an **unpersisted** ``CallRecord`` shell for this quote call."""
    record = CallRecord()
    record.id = uuid.uuid4()
    record.voice_extraction_id = voice_extraction_id
    record.phone_number = contractor.phone
    record.target_name = contractor.name
    record.target_context = {
        "address": listing_address,
        "contractor_source": contractor.source,
        "contractor_rating": contractor.rating,
        "contractor_reviews": contractor.reviews_count,
    }
    record.direction = CallDirection.outbound
    record.status = CallStatus.pending
    record.created_at = datetime.now(timezone.utc)
    return record


async def request_quote_via_voice(
    contractor: ContractorCandidate,
    listing: Any,
    pool_specs: PoolSpecs,
    max_call_duration_sec: int = 240,
    *,
    pipeline: _VoicePipeline | None = None,
) -> QuoteResult:
    """Place an outbound call and return the parsed quote.

    Args:
        contractor: Discovered + license-verified contractor.
        listing: :class:`app.models.pool_listing.PoolListing` — only
            ``address`` is required.
        pool_specs: Physical spec read aloud to the contractor.
        max_call_duration_sec: Hard cap on call length.
        pipeline: Optional voice-pipeline adapter override for tests.

    Returns:
        :class:`QuoteResult` — never raises for expected failure modes
        (timeout / no answer / decline). Only callers can propagate
        errors.
    """
    if not contractor.phone:
        return QuoteResult(
            contractor_name=contractor.name,
            contractor_phone="",
            status="call_failed",
            rating=contractor.rating,
            notes="contractor has no phone number",
        )

    pipe = pipeline or _default_pipeline()

    listing_address = getattr(listing, "address", None) or "the property"

    voice_extraction = _build_voice_extraction_shell(
        contractor=contractor,
        listing_address=listing_address,
        pool_specs=pool_specs,
        max_call_duration_sec=max_call_duration_sec,
    )
    call_record = _build_call_record_shell(
        contractor=contractor,
        listing_address=listing_address,
        voice_extraction_id=voice_extraction.id,
    )

    # Safety: regenerate the Gemini Live config but override the system
    # prompt with OUR TCPA-compliant prompt (the default builder may
    # pull a generic opener from ``call_script_template``).
    try:
        live_config = pipe.build_gemini_live_config(
            call_record=call_record, voice_extraction=voice_extraction
        )
    except Exception:  # pragma: no cover — defensive
        # Audit fix (security #3): do NOT echo the raw exception back to
        # the API surface — it may include credentials, query strings,
        # or SDK internals. Opaque status + full traceback in server log.
        logger.warning(
            "Failed to build Gemini Live config for contractor=%s",
            contractor.name,
            exc_info=True,
        )
        return QuoteResult(
            contractor_name=contractor.name,
            contractor_phone=contractor.phone,
            status="call_failed",
            rating=contractor.rating,
            notes="config_build_error",
        )

    quote_system_prompt = build_quote_system_prompt(
        contractor=contractor,
        listing_address=listing_address,
        pool_specs=pool_specs,
    )
    if isinstance(live_config, dict):
        live_config["system_prompt"] = quote_system_prompt

    # Audit fix (security #5): runtime contract check — the TCPA
    # disclosure MUST be embedded in the system prompt sent to Gemini
    # Live. If an adapter change or a future refactor ever drops the
    # preamble, fail LOUD here rather than let the call go live.
    _disclosure = build_disclosure_preamble()
    _outgoing_prompt = (
        live_config.get("system_prompt", "")
        if isinstance(live_config, dict)
        else ""
    )
    if _disclosure not in str(_outgoing_prompt):
        raise RuntimeError(
            "TCPA disclosure preamble missing from system prompt"
        )

    try:
        result = await pipe.create_outbound_call(
            call_record=call_record,
            voice_extraction=voice_extraction,
            db=None,  # unpersisted shell — adapter must tolerate None
        )
    except Exception:
        # Audit fix (security #4): opaque status only; detail in logs.
        logger.warning(
            "Outbound quote call failed for contractor=%s",
            contractor.name,
            exc_info=True,
        )
        return QuoteResult(
            contractor_name=contractor.name,
            contractor_phone=contractor.phone,
            status="call_failed",
            rating=contractor.rating,
            notes="call_failed",
        )

    return _interpret_call_result(
        contractor=contractor,
        call_record=call_record,
        result=result,
    )


def _interpret_call_result(
    contractor: ContractorCandidate,
    call_record: CallRecord,
    result: dict[str, Any],
) -> QuoteResult:
    """Map a Pipecat adapter result dict into a :class:`QuoteResult`."""
    raw_status = (result or {}).get("status")
    provider_call_id = (result or {}).get("call_sid") or (
        result or {}
    ).get("simulated_id")
    transcript = getattr(call_record, "transcript", None)
    recording_url = getattr(call_record, "recording_url", None)

    if raw_status in ("declined", "hangup_before_disclosure"):
        return QuoteResult(
            contractor_name=contractor.name,
            contractor_phone=contractor.phone,
            status=raw_status,  # type: ignore[arg-type]
            provider_call_id=provider_call_id,
            rating=contractor.rating,
            recording_url=recording_url,
            raw_transcript=transcript,
        )

    if raw_status == "no_answer":
        return QuoteResult(
            contractor_name=contractor.name,
            contractor_phone=contractor.phone,
            status="no_answer",
            provider_call_id=provider_call_id,
            rating=contractor.rating,
        )

    if raw_status == "failed":
        return QuoteResult(
            contractor_name=contractor.name,
            contractor_phone=contractor.phone,
            status="call_failed",
            provider_call_id=provider_call_id,
            rating=contractor.rating,
            notes=(result or {}).get("error"),
        )

    # Completed (real or simulated)
    low, high = parse_price_range(transcript)
    eta = parse_eta_weeks(transcript)

    if low is None and eta is None and transcript:
        parse_status: QuoteStatus = "parse_failed"
    elif low is None and eta is None and not transcript:
        parse_status = "call_failed"
    else:
        parse_status = "ok"

    return QuoteResult(
        contractor_name=contractor.name,
        contractor_phone=contractor.phone,
        status=parse_status,
        price_low_usd=low,
        price_high_usd=high,
        eta_weeks=eta,
        provider_call_id=provider_call_id,
        rating=contractor.rating,
        transcript_url=(result or {}).get("transcript_url"),
        recording_url=recording_url,
        raw_transcript=transcript,
        metadata={"adapter_status": raw_status},
    )
