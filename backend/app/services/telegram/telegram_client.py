"""Minimal async Telegram Bot API client.

Deliberately thin: we use ``httpx.AsyncClient`` directly so the footprint
stays small and tests can mock at the transport level. The bot token is
read from OpenClaw's ``~/.openclaw/openclaw.json`` under
``channels.telegram.botToken``; an ``AGENTARY_TELEGRAM_BOT_TOKEN``
environment variable overrides it for local development.

Only the two methods the Pool Concierge vertical needs are implemented:

* :meth:`TelegramClient.send_message`
* :meth:`TelegramClient.send_message_with_buttons`
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_API_BASE = "https://api.telegram.org"
_OPENCLAW_CONFIG_PATH = Path.home() / ".openclaw" / "openclaw.json"
_ENV_BOT_TOKEN = "AGENTARY_TELEGRAM_BOT_TOKEN"


@dataclass(frozen=True)
class InlineButton:
    """A single Telegram inline-keyboard button."""

    text: str
    callback_data: str


@dataclass(frozen=True)
class TelegramSendResult:
    """Result of a ``sendMessage`` call."""

    ok: bool
    message_id: str | None
    raw: dict[str, Any]


def _read_openclaw_bot_token() -> str | None:
    """Pull ``channels.telegram.botToken`` from OpenClaw config if present."""
    try:
        if not _OPENCLAW_CONFIG_PATH.exists():
            return None
        with _OPENCLAW_CONFIG_PATH.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("Unable to read OpenClaw config for Telegram: %s", exc)
        return None
    token = (
        data.get("channels", {})
        .get("telegram", {})
        .get("botToken")
    )
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def _resolve_bot_token() -> str | None:
    """Env var wins; fall back to OpenClaw config."""
    env = os.environ.get(_ENV_BOT_TOKEN)
    if env and env.strip():
        return env.strip()
    return _read_openclaw_bot_token()


def _build_inline_keyboard(
    rows: Sequence[Sequence[InlineButton]],
) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": btn.text, "callback_data": btn.callback_data}
                for btn in row
            ]
            for row in rows
        ]
    }


class TelegramClient:
    """Async wrapper around the Telegram Bot API.

    All I/O is gated so a missing bot token turns every send into a
    warning log + a dry-run success. This keeps tests deterministic
    (they can mock at either the client or :class:`httpx.AsyncClient`
    level) and keeps the pipeline from crashing when the token is not
    configured in CI.
    """

    def __init__(
        self,
        bot_token: str | None = None,
        *,
        api_base: str = _DEFAULT_API_BASE,
        client: httpx.AsyncClient | None = None,
        request_timeout: float = 15.0,
    ) -> None:
        self._token = bot_token if bot_token is not None else _resolve_bot_token()
        self._api_base = api_base.rstrip("/")
        self._client = client
        self._timeout = request_timeout
        self._owns_client = client is None

    def _url(self, method: str) -> str:
        if not self._token:
            raise RuntimeError(
                "Telegram bot token missing (set AGENTARY_TELEGRAM_BOT_TOKEN "
                "or configure ~/.openclaw/openclaw.json)."
            )
        return f"{self._api_base}/bot{self._token}/{method}"

    async def _post(
        self, method: str, payload: dict[str, Any]
    ) -> TelegramSendResult:
        """POST ``payload`` as JSON to the Bot API; return parsed result."""
        if not self._token:
            logger.warning(
                "Telegram token missing; dry-run send for method=%s payload=%s",
                method,
                payload,
            )
            return TelegramSendResult(
                ok=False, message_id=None, raw={"dry_run": True}
            )

        client = self._client or httpx.AsyncClient(timeout=self._timeout)
        try:
            resp = await client.post(self._url(method), json=payload)
            raw: dict[str, Any] = {}
            try:
                raw = resp.json()
            except ValueError:
                raw = {"status_code": resp.status_code}
            ok = bool(raw.get("ok"))
            message_id = None
            if ok:
                result = raw.get("result") or {}
                mid = result.get("message_id")
                if mid is not None:
                    message_id = str(mid)
            return TelegramSendResult(ok=ok, message_id=message_id, raw=raw)
        except httpx.HTTPError as exc:
            logger.warning("Telegram %s failed: %s", method, exc)
            return TelegramSendResult(
                ok=False, message_id=None, raw={"error": str(exc)}
            )
        finally:
            if self._owns_client and self._client is None:
                await client.aclose()

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        parse_mode: str | None = "Markdown",
        disable_web_page_preview: bool = True,
    ) -> TelegramSendResult:
        """Send a plain text message to ``chat_id``."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return await self._post("sendMessage", payload)

    async def send_message_with_buttons(
        self,
        chat_id: str,
        text: str,
        button_rows: Sequence[Sequence[InlineButton]],
        *,
        parse_mode: str | None = "Markdown",
        disable_web_page_preview: bool = True,
    ) -> TelegramSendResult:
        """Send a message with an inline keyboard attached."""
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
            "reply_markup": _build_inline_keyboard(button_rows),
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        return await self._post("sendMessage", payload)

    async def answer_callback_query(
        self, callback_query_id: str, text: str | None = None
    ) -> TelegramSendResult:
        """Acknowledge an inline-keyboard button tap."""
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        return await self._post("answerCallbackQuery", payload)


# Module-level convenience wrappers ---------------------------------------
async def send_message(
    chat_id: str,
    text: str,
    *,
    client: TelegramClient | None = None,
) -> TelegramSendResult:
    """Construct a default client and call :meth:`TelegramClient.send_message`."""
    tg = client or TelegramClient()
    return await tg.send_message(chat_id, text)


async def send_message_with_buttons(
    chat_id: str,
    text: str,
    button_rows: Sequence[Sequence[InlineButton]],
    *,
    client: TelegramClient | None = None,
) -> TelegramSendResult:
    """Construct a default client and send an inline-keyboard message."""
    tg = client or TelegramClient()
    return await tg.send_message_with_buttons(chat_id, text, button_rows)
