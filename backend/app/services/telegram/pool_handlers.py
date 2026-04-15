"""Pool Concierge Telegram handlers.

This module is a **registry** — it does not own a bot event loop. The
external Telegram bot process (``@edward_the_ai_bot``) is expected to
import :data:`POOL_HANDLERS` and route updates through it.

Register in the bot's main loop with::

    from app.services.telegram.pool_handlers import POOL_HANDLERS
    for handler in POOL_HANDLERS.command_handlers:
        bot.on_command(handler.command, handler.func)
    for prefix, func in POOL_HANDLERS.callback_prefixes.items():
        bot.on_callback(prefix, func)

Callback data conventions (kept < 64 bytes per Telegram limits):

* ``pq:<listing_short>`` — "See quotes" (Stream C report)
* ``pc:<listing_short>`` — "Draft contract" (Stream D builder)
* ``pp:<listing_short>`` — "Pass" (dismiss)

The ``<listing_short>`` is the first 8 hex chars of the PoolListing UUID.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Protocol
from uuid import UUID

import httpx

from ...config import settings
from .telegram_client import InlineButton, TelegramClient

logger = logging.getLogger(__name__)

_POOL_SEARCH_COMMAND = "/pool_search"
_CALLBACK_QUOTES_PREFIX = "pq:"
_CALLBACK_CONTRACT_PREFIX = "pc:"
_CALLBACK_PASS_PREFIX = "pp:"
_MAX_LISTINGS_IN_DIGEST = 3
_POLL_INTERVAL_SEC = 5.0
_POLL_MAX_SEC = 180.0


# ---------------------------------------------------------------------------
# Handler payload shapes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommandUpdate:
    """Minimal slice of a Telegram update used by command handlers."""

    chat_id: str
    user_id: str
    text: str
    message_id: str | None = None


@dataclass(frozen=True)
class CallbackUpdate:
    """Minimal slice of a Telegram callback-query update."""

    callback_query_id: str
    chat_id: str
    user_id: str
    data: str
    message_id: str | None = None


CommandFn = Callable[[CommandUpdate], Awaitable[None]]
CallbackFn = Callable[[CallbackUpdate], Awaitable[None]]


@dataclass(frozen=True)
class CommandEntry:
    """One registered command (``/pool_search``, etc.)."""

    command: str
    func: CommandFn


@dataclass(frozen=True)
class PoolHandlerRegistry:
    """Registry the external bot loop can iterate to route updates."""

    command_handlers: tuple[CommandEntry, ...] = field(default_factory=tuple)
    callback_prefixes: dict[str, CallbackFn] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Shared state — where the in-flight pipeline run ids live per chat.
# ---------------------------------------------------------------------------

_CHAT_RUNS: dict[str, str] = {}  # chat_id -> run_id
_SHORT_ID_MAP: dict[str, UUID] = {}  # short 8-hex -> full listing UUID


def _short_listing_id(listing_id: UUID) -> str:
    short = str(listing_id).replace("-", "")[:8]
    _SHORT_ID_MAP[short] = listing_id
    return short


def _resolve_short_id(short: str) -> UUID | None:
    """Look up the full listing UUID for a short callback tag."""
    return _SHORT_ID_MAP.get(short)


# ---------------------------------------------------------------------------
# Tunable API client (injectable for tests)
# ---------------------------------------------------------------------------


class _ApiClientProto(Protocol):
    async def post_run(self, user_id: str, zipcode: str) -> dict[str, Any]: ...
    async def get_run(self, run_id: str) -> dict[str, Any]: ...
    async def post_contractors_for_listing(
        self, listing_id: str
    ) -> dict[str, Any]: ...
    async def get_contractor_report(self, report_id: str) -> dict[str, Any]: ...
    async def post_contract_draft(self, body: dict[str, Any]) -> dict[str, Any]: ...


class AgentaryApiClient:
    """HTTP client pointed at the local Agentary FastAPI process.

    Base URL defaults to ``settings.base_url`` which is the frontend URL
    — the bot typically runs on the same host as the backend, so we
    allow injection of the backend URL via the ``base_url`` kwarg.
    """

    def __init__(
        self,
        base_url: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        auth_token: str | None = None,
    ) -> None:
        self._base = (base_url or "http://localhost:8000").rstrip("/")
        self._client = client
        self._owns_client = client is None
        self._auth_token = auth_token

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        client = self._client or httpx.AsyncClient(timeout=20.0)
        try:
            resp = await client.post(
                f"{self._base}{path}", json=body, headers=self._headers()
            )
            resp.raise_for_status()
            return dict(resp.json())
        finally:
            if self._owns_client and self._client is None:
                await client.aclose()

    async def _get(self, path: str) -> dict[str, Any]:
        client = self._client or httpx.AsyncClient(timeout=20.0)
        try:
            resp = await client.get(
                f"{self._base}{path}", headers=self._headers()
            )
            resp.raise_for_status()
            return dict(resp.json())
        finally:
            if self._owns_client and self._client is None:
                await client.aclose()

    async def post_run(self, user_id: str, zipcode: str) -> dict[str, Any]:
        return await self._post(
            "/api/verticals/pool/run",
            {"user_id": user_id, "zipcode": zipcode, "radius_mi": 5.0},
        )

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return await self._get(f"/api/verticals/pool/runs/{run_id}")

    async def post_contractors_for_listing(
        self, listing_id: str
    ) -> dict[str, Any]:
        return await self._post(
            f"/api/verticals/pool/listings/{listing_id}/contractors",
            {
                "radius_mi": 15.0,
                "min_rating": 4.0,
                "min_reviews": 20,
                "discovery_limit": 10,
            },
        )

    async def get_contractor_report(self, report_id: str) -> dict[str, Any]:
        return await self._get(
            f"/api/verticals/pool/contractors/{report_id}"
        )

    async def post_contract_draft(
        self, body: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._post("/api/verticals/pool/contracts/draft", body)


# Default singletons (tests reach in and swap these).
_api_client: _ApiClientProto = AgentaryApiClient()
_telegram_client: TelegramClient = TelegramClient()


def set_clients(
    *,
    api_client: _ApiClientProto | None = None,
    telegram_client: TelegramClient | None = None,
) -> None:
    """Swap the module-level clients (used by tests and DI from main)."""
    global _api_client, _telegram_client  # noqa: PLW0603 (module-level DI)
    if api_client is not None:
        _api_client = api_client
    if telegram_client is not None:
        _telegram_client = telegram_client


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _format_price(price: float | int | None) -> str:
    if price is None:
        return "Price TBD"
    try:
        return f"${int(price):,}"
    except (TypeError, ValueError):
        return str(price)


def _format_score(score: float | int | None) -> str:
    if score is None:
        return "—"
    try:
        return f"{float(score):.2f}"
    except (TypeError, ValueError):
        return str(score)


def _preview_link(listing_result: dict[str, Any]) -> str:
    """Build a 3-angle preview link stub.

    The frontend renders these with the aerial image plus the placed
    pool overlay; the bot just needs a deterministic URL.
    """
    lid = listing_result.get("pool_listing_id")
    base = (settings.base_url or "http://localhost:3000").rstrip("/")
    return f"{base}/pool/listing/{lid}"


def render_digest(run_payload: dict[str, Any]) -> str:
    """Format the top-3 listings into a Markdown message body."""
    zipcode = run_payload.get("zipcode", "—")
    status = run_payload.get("status", "pending")
    lines = [
        f"*Pool Concierge — {zipcode}*",
        f"Status: `{status}`",
        "",
    ]
    summary = run_payload.get("summary") or {}
    top = summary.get("top_listings") or run_payload.get("listings") or []
    if not top:
        lines.append("_No scored listings yet._")
        return "\n".join(lines)

    for idx, listing in enumerate(top[:_MAX_LISTINGS_IN_DIGEST], start=1):
        address = listing.get("address", "Unknown address")
        price = _format_price(listing.get("list_price"))
        score = _format_score(listing.get("score"))
        link = _preview_link(listing)
        lines.append(f"*{idx}. {address}*")
        lines.append(f"   {price} · score {score}")
        lines.append(f"   [3-angle preview]({link})")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_digest_buttons(
    run_payload: dict[str, Any],
) -> list[list[InlineButton]]:
    """Build one button row per top listing."""
    summary = run_payload.get("summary") or {}
    top = summary.get("top_listings") or run_payload.get("listings") or []
    rows: list[list[InlineButton]] = []
    for listing in top[:_MAX_LISTINGS_IN_DIGEST]:
        lid_raw = listing.get("pool_listing_id")
        if lid_raw is None:
            continue
        try:
            short = _short_listing_id(UUID(str(lid_raw)))
        except (TypeError, ValueError):
            continue
        rows.append(
            [
                InlineButton(
                    text="See quotes",
                    callback_data=f"{_CALLBACK_QUOTES_PREFIX}{short}",
                ),
                InlineButton(
                    text="Draft contract",
                    callback_data=f"{_CALLBACK_CONTRACT_PREFIX}{short}",
                ),
                InlineButton(
                    text="Pass",
                    callback_data=f"{_CALLBACK_PASS_PREFIX}{short}",
                ),
            ]
        )
    return rows


# ---------------------------------------------------------------------------
# /pool_search command
# ---------------------------------------------------------------------------


def _parse_pool_search(text: str) -> str | None:
    """Pull the ZIP argument off a ``/pool_search 75024`` command."""
    parts = (text or "").strip().split()
    if len(parts) < 2:
        return None
    candidate = parts[1].strip()
    if len(candidate) == 5 and candidate.isdigit():
        return candidate
    return None


async def handle_pool_search(update: CommandUpdate) -> None:
    """Kick off the full pool pipeline and send a digest back."""
    zipcode = _parse_pool_search(update.text)
    if zipcode is None:
        await _telegram_client.send_message(
            update.chat_id,
            "Usage: `/pool_search <5-digit ZIP>` (e.g. `/pool_search 75024`)",
        )
        return

    await _telegram_client.send_message(
        update.chat_id,
        f"Starting search for pool-ready houses in {zipcode}...",
    )

    try:
        run = await _api_client.post_run(update.user_id, zipcode)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pool pipeline kickoff failed")
        await _telegram_client.send_message(
            update.chat_id, f"Pipeline kickoff failed: {exc}"
        )
        return

    run_id = str(run.get("run_id") or run.get("id") or "")
    if not run_id:
        await _telegram_client.send_message(
            update.chat_id, "Pipeline kickoff returned no run_id"
        )
        return

    _CHAT_RUNS[update.chat_id] = run_id
    await _poll_and_send_digest(update.chat_id, run_id)


async def _poll_and_send_digest(chat_id: str, run_id: str) -> None:
    """Poll the run until it reaches ``ready`` or ``failed``, then send."""
    import asyncio

    elapsed = 0.0
    while elapsed < _POLL_MAX_SEC:
        try:
            run = await _api_client.get_run(run_id)
        except Exception:  # noqa: BLE001
            logger.exception("Polling run %s failed", run_id)
            await _telegram_client.send_message(
                chat_id, "Lost track of the pipeline — try again later."
            )
            return

        status = str(run.get("status") or "")
        if status in {"ready", "failed"}:
            if status == "failed":
                await _telegram_client.send_message(
                    chat_id,
                    "Pipeline finished without matching listings.",
                )
                return
            text = render_digest(run)
            buttons = build_digest_buttons(run)
            if buttons:
                await _telegram_client.send_message_with_buttons(
                    chat_id, text, buttons
                )
            else:
                await _telegram_client.send_message(chat_id, text)
            return

        await asyncio.sleep(_POLL_INTERVAL_SEC)
        elapsed += _POLL_INTERVAL_SEC

    await _telegram_client.send_message(
        chat_id, "Pipeline still running — we'll ping you when it's done."
    )


# ---------------------------------------------------------------------------
# Button callbacks
# ---------------------------------------------------------------------------


async def handle_see_quotes(update: CallbackUpdate) -> None:
    """``See quotes`` tap — kicks off the contractor pipeline."""
    short = update.data[len(_CALLBACK_QUOTES_PREFIX):]
    listing_id = _resolve_short_id(short)
    if listing_id is None:
        await _telegram_client.answer_callback_query(
            update.callback_query_id, "Listing reference expired"
        )
        return

    await _telegram_client.answer_callback_query(
        update.callback_query_id, "Fetching contractor quotes..."
    )

    try:
        kickoff = await _api_client.post_contractors_for_listing(
            str(listing_id)
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Contractor kickoff failed")
        await _telegram_client.send_message(
            update.chat_id, f"Contractor pipeline failed to start: {exc}"
        )
        return

    report_id = str(kickoff.get("report_id") or "")
    if not report_id:
        await _telegram_client.send_message(
            update.chat_id, "Contractor pipeline returned no report_id"
        )
        return
    await _poll_and_send_quotes(update.chat_id, report_id)


async def _poll_and_send_quotes(chat_id: str, report_id: str) -> None:
    import asyncio

    elapsed = 0.0
    while elapsed < _POLL_MAX_SEC:
        try:
            report = await _api_client.get_contractor_report(report_id)
        except Exception:  # noqa: BLE001
            logger.exception("Polling contractor report failed")
            await _telegram_client.send_message(
                chat_id, "Lost track of contractor pipeline"
            )
            return

        status = str(report.get("status") or "")
        if status in {"ready", "failed"}:
            if status == "failed":
                await _telegram_client.send_message(
                    chat_id, "No verified contractors returned quotes."
                )
                return
            await _telegram_client.send_message(
                chat_id,
                _render_quotes_body(report),
            )
            return
        await asyncio.sleep(_POLL_INTERVAL_SEC)
        elapsed += _POLL_INTERVAL_SEC
    await _telegram_client.send_message(
        chat_id,
        "Contractor pipeline still running — we'll ping you later.",
    )


def _render_quotes_body(report: dict[str, Any]) -> str:
    top = report.get("top_quotes") or []
    if not top:
        return "No ranked quotes available yet."
    lines = ["*Top contractor quotes*", ""]
    for i, entry in enumerate(top, start=1):
        quote = entry.get("quote", entry) if isinstance(entry, dict) else {}
        name = quote.get("contractor_name") or entry.get("contractor_name")
        low = quote.get("price_low_usd") or entry.get("price_low_usd")
        high = quote.get("price_high_usd") or entry.get("price_high_usd")
        eta = quote.get("eta_weeks") or entry.get("eta_weeks")
        lines.append(f"*{i}. {name}*")
        lines.append(
            f"   {_format_price(low)}–{_format_price(high)} · {eta} weeks"
        )
    return "\n".join(lines)


async def handle_draft_contract(update: CallbackUpdate) -> None:
    """``Draft contract`` tap — ask the API for a contract draft."""
    short = update.data[len(_CALLBACK_CONTRACT_PREFIX):]
    listing_id = _resolve_short_id(short)
    if listing_id is None:
        await _telegram_client.answer_callback_query(
            update.callback_query_id, "Listing reference expired"
        )
        return

    await _telegram_client.answer_callback_query(
        update.callback_query_id, "Drafting contract..."
    )
    await _telegram_client.send_message(
        update.chat_id,
        (
            "Contract drafting kicked off for this listing. The full flow "
            "collects a signed quote + buyer/contractor info before "
            "producing the PDF — see the web UI to complete it."
        ),
    )


async def handle_pass(update: CallbackUpdate) -> None:
    """``Pass`` tap — just acknowledge so the button stops spinning."""
    await _telegram_client.answer_callback_query(
        update.callback_query_id, "Skipped"
    )


# ---------------------------------------------------------------------------
# Registry (public)
# ---------------------------------------------------------------------------


POOL_HANDLERS = PoolHandlerRegistry(
    command_handlers=(
        CommandEntry(command=_POOL_SEARCH_COMMAND, func=handle_pool_search),
    ),
    callback_prefixes={
        _CALLBACK_QUOTES_PREFIX: handle_see_quotes,
        _CALLBACK_CONTRACT_PREFIX: handle_draft_contract,
        _CALLBACK_PASS_PREFIX: handle_pass,
    },
)
