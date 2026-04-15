"""Unit tests for the Pool Concierge Telegram handlers (Stream E).

All Telegram API and Agentary HTTP traffic is mocked — these tests run
fully offline. Handlers are invoked directly with synthetic
:class:`CommandUpdate` / :class:`CallbackUpdate` objects.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from app.services.telegram import pool_handlers
from app.services.telegram.pool_handlers import (
    CallbackUpdate,
    CommandUpdate,
    POOL_HANDLERS,
    build_digest_buttons,
    handle_draft_contract,
    handle_pass,
    handle_pool_search,
    handle_see_quotes,
    render_digest,
    set_clients,
)
from app.services.telegram.telegram_client import (
    InlineButton,
    TelegramSendResult,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class FakeTelegramClient:
    """Captures every ``send_*`` call for assertions."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    button_messages: list[dict[str, Any]] = field(default_factory=list)
    callbacks: list[dict[str, Any]] = field(default_factory=list)

    async def send_message(
        self, chat_id: str, text: str, **_kwargs: Any
    ) -> TelegramSendResult:
        self.messages.append({"chat_id": chat_id, "text": text})
        return TelegramSendResult(
            ok=True, message_id="m-123", raw={"ok": True}
        )

    async def send_message_with_buttons(
        self,
        chat_id: str,
        text: str,
        button_rows: list[list[InlineButton]],
        **_kwargs: Any,
    ) -> TelegramSendResult:
        self.button_messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "rows": [
                    [{"text": b.text, "data": b.callback_data} for b in row]
                    for row in button_rows
                ],
            }
        )
        return TelegramSendResult(
            ok=True, message_id="m-btn-1", raw={"ok": True}
        )

    async def answer_callback_query(
        self, callback_query_id: str, text: str | None = None
    ) -> TelegramSendResult:
        self.callbacks.append({"id": callback_query_id, "text": text})
        return TelegramSendResult(
            ok=True, message_id=None, raw={"ok": True}
        )


@dataclass
class FakeApiClient:
    """Stubs the Agentary HTTP API used by the handlers."""

    run_payload: dict[str, Any] = field(default_factory=dict)
    report_payload: dict[str, Any] = field(default_factory=dict)
    contractor_kickoff_payload: dict[str, Any] = field(default_factory=dict)
    calls: list[tuple[str, dict[str, Any] | None]] = field(
        default_factory=list
    )
    run_sequence: list[dict[str, Any]] | None = None
    report_sequence: list[dict[str, Any]] | None = None

    async def post_run(self, user_id: str, zipcode: str) -> dict[str, Any]:
        self.calls.append(
            ("post_run", {"user_id": user_id, "zipcode": zipcode})
        )
        return dict(self.run_payload)

    async def get_run(self, run_id: str) -> dict[str, Any]:
        self.calls.append(("get_run", {"run_id": run_id}))
        if self.run_sequence:
            return dict(self.run_sequence.pop(0))
        return dict(self.run_payload)

    async def post_contractors_for_listing(
        self, listing_id: str
    ) -> dict[str, Any]:
        self.calls.append(
            ("post_contractors", {"listing_id": listing_id})
        )
        return dict(self.contractor_kickoff_payload)

    async def get_contractor_report(self, report_id: str) -> dict[str, Any]:
        self.calls.append(("get_contractor_report", {"id": report_id}))
        if self.report_sequence:
            return dict(self.report_sequence.pop(0))
        return dict(self.report_payload)

    async def post_contract_draft(
        self, body: dict[str, Any]
    ) -> dict[str, Any]:
        self.calls.append(("post_contract_draft", body))
        return {"draft_id": "d-123"}


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def tg() -> FakeTelegramClient:
    return FakeTelegramClient()


@pytest.fixture
def api() -> FakeApiClient:
    return FakeApiClient()


@pytest.fixture(autouse=True)
def _patch_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove the poll interval so tests finish instantly."""

    async def _no_sleep(*_a: Any, **_k: Any) -> None:
        return None

    import asyncio

    monkeypatch.setattr(asyncio, "sleep", _no_sleep)


@pytest.fixture(autouse=True)
def _wire_clients(
    tg: FakeTelegramClient, api: FakeApiClient
) -> None:
    set_clients(api_client=api, telegram_client=tg)  # type: ignore[arg-type]


def _scored_listing_payload(
    listing_id: str, address: str, price: int, score: float
) -> dict[str, Any]:
    return {
        "pool_listing_id": listing_id,
        "address": address,
        "list_price": price,
        "score": score,
        "fit_reason": "Large backyard",
        "max_pool_size": "20x40",
        "aerial_image_url": "https://mapbox.test/tile.png",
        "listing_url": "https://zillow.test/1",
        "contractor_report_id": None,
        "contractor_status": "ready",
        "quote_count": 3,
        "top_quotes": [],
        "permit_jurisdiction": "plano_tx",
        "permit_item_count": 5,
    }


def _ready_run_payload(zipcode: str = "75024") -> dict[str, Any]:
    lid1 = str(uuid4())
    lid2 = str(uuid4())
    lid3 = str(uuid4())
    return {
        "run_id": str(uuid4()),
        "zipcode": zipcode,
        "status": "ready",
        "total_listings": 5,
        "ready_listings": 3,
        "summary": {
            "top_listings": [
                _scored_listing_payload(
                    lid1, "2025 Legacy Dr, Plano, TX 75024", 1_100_000, 0.93
                ),
                _scored_listing_payload(
                    lid2, "1001 Independence Pkwy, Plano, TX 75075",
                    850_000, 0.81,
                ),
                _scored_listing_payload(
                    lid3, "700 Tiny Ct, Plano, TX 75023", 520_000, 0.65
                ),
            ],
        },
    }


# ---------------------------------------------------------------------------
# Registry sanity
# ---------------------------------------------------------------------------


def test_registry_exposes_expected_commands_and_callbacks() -> None:
    commands = [entry.command for entry in POOL_HANDLERS.command_handlers]
    assert "/pool_search" in commands

    assert "pq:" in POOL_HANDLERS.callback_prefixes
    assert "pc:" in POOL_HANDLERS.callback_prefixes
    assert "pp:" in POOL_HANDLERS.callback_prefixes


# ---------------------------------------------------------------------------
# /pool_search flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pool_search_rejects_missing_zip(
    tg: FakeTelegramClient, api: FakeApiClient
) -> None:
    await handle_pool_search(
        CommandUpdate(
            chat_id="c1", user_id="u1", text="/pool_search"
        )
    )
    assert tg.messages
    assert "Usage" in tg.messages[0]["text"]
    assert api.calls == []  # never hit the API


@pytest.mark.asyncio
async def test_pool_search_rejects_non_numeric_zip(
    tg: FakeTelegramClient, api: FakeApiClient
) -> None:
    await handle_pool_search(
        CommandUpdate(chat_id="c1", user_id="u1", text="/pool_search PLANO")
    )
    assert "Usage" in tg.messages[0]["text"]
    assert api.calls == []


@pytest.mark.asyncio
async def test_pool_search_happy_path_posts_digest(
    tg: FakeTelegramClient, api: FakeApiClient
) -> None:
    run_id = str(uuid4())
    pending = {"run_id": run_id, "zipcode": "75024", "status": "pending"}
    ready = _ready_run_payload("75024")
    ready["run_id"] = run_id

    api.run_payload = {"run_id": run_id, "status": "pending"}
    api.run_sequence = [pending, ready]

    await handle_pool_search(
        CommandUpdate(
            chat_id="c1", user_id=str(uuid4()), text="/pool_search 75024"
        )
    )

    # First text message is the "Starting search..." ack.
    assert any("Starting search" in m["text"] for m in tg.messages)
    # Digest landed as a button message with 3 rows of 3 buttons.
    assert tg.button_messages, "expected a digest button message"
    digest = tg.button_messages[-1]
    assert "75024" in digest["text"]
    assert len(digest["rows"]) == 3
    for row in digest["rows"]:
        prefixes = {btn["data"][:3] for btn in row}
        assert prefixes == {"pq:", "pc:", "pp:"}


@pytest.mark.asyncio
async def test_pool_search_surfaces_failed_status(
    tg: FakeTelegramClient, api: FakeApiClient
) -> None:
    run_id = str(uuid4())
    api.run_payload = {"run_id": run_id, "status": "pending"}
    api.run_sequence = [
        {"run_id": run_id, "zipcode": "75024", "status": "failed"}
    ]

    await handle_pool_search(
        CommandUpdate(
            chat_id="c1", user_id="u1", text="/pool_search 75024"
        )
    )
    assert any("finished without matching" in m["text"] for m in tg.messages)
    assert tg.button_messages == []


@pytest.mark.asyncio
async def test_pool_search_handles_kickoff_exception(
    tg: FakeTelegramClient, api: FakeApiClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _boom(*a: Any, **kw: Any) -> dict[str, Any]:
        raise RuntimeError("API down")

    monkeypatch.setattr(api, "post_run", _boom)
    await handle_pool_search(
        CommandUpdate(
            chat_id="c1", user_id="u1", text="/pool_search 75024"
        )
    )
    assert any("Pipeline kickoff failed" in m["text"] for m in tg.messages)


# ---------------------------------------------------------------------------
# Button callbacks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_see_quotes_kicks_contractor_pipeline_and_polls(
    tg: FakeTelegramClient, api: FakeApiClient
) -> None:
    # First seed the short-id map by building digest buttons.
    ready = _ready_run_payload()
    rows = build_digest_buttons(ready)
    assert rows
    quote_btn = rows[0][0]
    assert quote_btn.callback_data.startswith("pq:")

    report_id = str(uuid4())
    api.contractor_kickoff_payload = {
        "report_id": report_id,
        "status": "pending",
    }
    api.report_sequence = [
        {"report_id": report_id, "status": "quoting"},
        {
            "report_id": report_id,
            "status": "ready",
            "top_quotes": [
                {
                    "rank": 1,
                    "score": 0.9,
                    "quote": {
                        "contractor_name": "BlueWave Pools",
                        "price_low_usd": 60_000,
                        "price_high_usd": 80_000,
                        "eta_weeks": 8,
                    },
                },
            ],
        },
    ]

    await handle_see_quotes(
        CallbackUpdate(
            callback_query_id="cbq-1",
            chat_id="c1",
            user_id="u1",
            data=quote_btn.callback_data,
        )
    )

    # callback was answered, contractor pipeline kicked, quotes rendered.
    assert tg.callbacks[0]["id"] == "cbq-1"
    assert any("Top contractor quotes" in m["text"] for m in tg.messages)
    assert any("BlueWave Pools" in m["text"] for m in tg.messages)
    kinds = [name for name, _ in api.calls]
    assert "post_contractors" in kinds
    assert "get_contractor_report" in kinds


@pytest.mark.asyncio
async def test_see_quotes_rejects_expired_short_id(
    tg: FakeTelegramClient, api: FakeApiClient
) -> None:
    await handle_see_quotes(
        CallbackUpdate(
            callback_query_id="cbq-x",
            chat_id="c1",
            user_id="u1",
            data="pq:ffffffff",
        )
    )
    assert tg.callbacks[0]["text"] == "Listing reference expired"
    assert tg.messages == []


@pytest.mark.asyncio
async def test_draft_contract_sends_confirmation(
    tg: FakeTelegramClient, api: FakeApiClient
) -> None:
    ready = _ready_run_payload()
    rows = build_digest_buttons(ready)
    contract_btn = rows[0][1]
    assert contract_btn.callback_data.startswith("pc:")

    await handle_draft_contract(
        CallbackUpdate(
            callback_query_id="cbq-2",
            chat_id="c1",
            user_id="u1",
            data=contract_btn.callback_data,
        )
    )
    assert tg.callbacks[0]["text"] == "Drafting contract..."
    assert any("Contract drafting" in m["text"] for m in tg.messages)


@pytest.mark.asyncio
async def test_pass_just_acknowledges(
    tg: FakeTelegramClient, api: FakeApiClient
) -> None:
    ready = _ready_run_payload()
    rows = build_digest_buttons(ready)
    pass_btn = rows[0][2]
    assert pass_btn.callback_data.startswith("pp:")

    await handle_pass(
        CallbackUpdate(
            callback_query_id="cbq-3",
            chat_id="c1",
            user_id="u1",
            data=pass_btn.callback_data,
        )
    )
    assert tg.callbacks[0]["text"] == "Skipped"
    assert tg.messages == []


# ---------------------------------------------------------------------------
# Rendering unit tests
# ---------------------------------------------------------------------------


def test_render_digest_has_three_listings_and_preview_links() -> None:
    ready = _ready_run_payload("75024")
    text = render_digest(ready)
    assert "Pool Concierge — 75024" in text
    # All three addresses are present.
    assert "Legacy Dr" in text
    assert "Independence Pkwy" in text
    assert "Tiny Ct" in text
    # Preview links include pool/listing path.
    assert text.count("/pool/listing/") == 3


def test_render_digest_handles_empty_summary() -> None:
    text = render_digest(
        {"zipcode": "75024", "status": "pending", "summary": None}
    )
    assert "No scored listings yet" in text


def test_build_digest_buttons_caps_at_three_rows() -> None:
    summary = {
        "zipcode": "75024",
        "status": "ready",
        "summary": {
            "top_listings": [
                _scored_listing_payload(str(uuid4()), f"addr {i}", 500_000, 0.9)
                for i in range(5)
            ],
        },
    }
    rows = build_digest_buttons(summary)
    assert len(rows) == 3
    for row in rows:
        assert len(row) == 3


def test_build_digest_buttons_skips_entries_without_listing_id() -> None:
    summary = {
        "zipcode": "75024",
        "status": "ready",
        "summary": {
            "top_listings": [
                {"address": "missing id", "list_price": 100, "score": 1},
            ],
        },
    }
    assert build_digest_buttons(summary) == []
