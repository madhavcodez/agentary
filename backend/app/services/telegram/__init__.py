"""Telegram bot integration services.

This package holds thin wrappers around the Telegram Bot API plus the
command/callback handlers that the external bot process routes inbound
updates to.

Public surface
--------------
* :func:`send_message` / :func:`send_message_with_buttons` — async
  helpers built on ``httpx`` so they can be called from FastAPI /
  background tasks without pulling in a full Telegram framework.
* :data:`POOL_HANDLERS` — a registry of handler entries the external
  bot loop iterates to route ``/pool_search`` and pool-listing button
  callbacks (see :mod:`app.services.telegram.pool_handlers`).
"""
from __future__ import annotations

from .pool_handlers import POOL_HANDLERS, PoolHandlerRegistry
from .telegram_client import (
    InlineButton,
    TelegramClient,
    TelegramSendResult,
    send_message,
    send_message_with_buttons,
)

__all__ = [
    "InlineButton",
    "POOL_HANDLERS",
    "PoolHandlerRegistry",
    "TelegramClient",
    "TelegramSendResult",
    "send_message",
    "send_message_with_buttons",
]
