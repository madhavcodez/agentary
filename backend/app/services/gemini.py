"""Backward-compat shim — delegates to ``platform.infrastructure.providers.gemini``.

This module used to wrap ``google.genai`` directly. The SDK code has moved
into the unified provider; the public callables below are preserved so the
many existing consumers don't need to change in this PR. New code should
import from ``app.platform.infrastructure.providers`` directly.
"""
from __future__ import annotations

from typing import Any

from ..platform.infrastructure.providers.gemini import (
    DEFAULT_FLASH_MODEL,
    gemini_provider,
)


def get_client() -> Any:
    """Return the underlying genai client (kept for legacy callers)."""
    return gemini_provider._ensure_client()  # noqa: SLF001 - intentional shim


async def embed_text(
    text: str, task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[float]:
    return await gemini_provider.embed(text, task_type=task_type)


async def generate_structured(
    prompt: str,
    schema_hint: str = "",
    model: str = DEFAULT_FLASH_MODEL,
) -> dict[str, Any]:
    return await gemini_provider.generate_json(
        prompt, schema_hint=schema_hint, model=model
    )


async def generate_text(
    prompt: str, system: str = "", model: str = DEFAULT_FLASH_MODEL
) -> str:
    return await gemini_provider.generate_text(prompt, system=system, model=model)
