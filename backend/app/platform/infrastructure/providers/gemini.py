"""Unified Gemini adapter.

Consolidates the previous module-level helpers in ``services/gemini.py`` so
that domain code never imports ``google.genai`` directly. The legacy module
keeps thin re-export shims for backward compatibility during the modular
reorg.

Design choices
- Single lazy ``Client`` shared across all calls (Gemini's SDK is async-safe
  for read calls).
- All exposed calls go through ``gemini_breaker`` so circuit-state is
  uniform.
- JSON parsing helpers handle the markdown-fence response shape Gemini
  occasionally emits.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from google import genai
from google.genai import types

from ....config import settings
from ....services.circuit_breakers import gemini_breaker

logger = logging.getLogger(__name__)

DEFAULT_FLASH_MODEL = "gemini-2.5-flash"
DEFAULT_PRO_MODEL = "gemini-2.5-pro"
DEFAULT_EMBED_MODEL = "gemini-embedding-001"


class GeminiUnavailable(RuntimeError):
    """Raised when GEMINI_API_KEY is unset or the client cannot be built."""


class GeminiProvider:
    """Adapter over the google-genai SDK."""

    def __init__(self) -> None:
        self._client: genai.Client | None = None

    def _ensure_client(self) -> genai.Client:
        if self._client is None:
            if not settings.gemini_api_key:
                raise GeminiUnavailable("GEMINI_API_KEY not configured")
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(settings.gemini_api_key)

    @gemini_breaker
    async def embed(
        self,
        text: str,
        *,
        task_type: str = "RETRIEVAL_DOCUMENT",
        model: str = DEFAULT_EMBED_MODEL,
    ) -> list[float]:
        """Return an embedding vector for ``text``."""
        client = self._ensure_client()
        result = client.models.embed_content(
            model=model,
            contents=text,
            config=types.EmbedContentConfig(task_type=task_type),
        )
        return result.embeddings[0].values

    @gemini_breaker
    async def generate_text(
        self,
        prompt: str,
        *,
        system: str = "",
        model: str = DEFAULT_FLASH_MODEL,
        temperature: float = 0.7,
    ) -> str:
        """Plain free-form text generation."""
        client = self._ensure_client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system or "You are a helpful AI assistant.",
                temperature=temperature,
            ),
        )
        return response.text or ""

    @gemini_breaker
    async def generate_json(
        self,
        prompt: str,
        *,
        schema_hint: str = "",
        model: str = DEFAULT_FLASH_MODEL,
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """Generate structured JSON. Handles markdown-fenced responses."""
        client = self._ensure_client()
        system_instruction = (
            "You are an expert data extraction assistant. Return valid JSON only."
        )
        if schema_hint:
            system_instruction += f"\n\nExpected output schema:\n{schema_hint}"

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        return _parse_json_strict_or_loose(response.text or "")


def _parse_json_strict_or_loose(text: str) -> dict[str, Any]:
    """Parse JSON; fall back to extracting the first ``{...}`` block.

    Gemini occasionally wraps JSON in ```` ```json ``` ```` fences or
    inserts trailing prose — handle both shapes so callers can rely on a
    plain dict.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end])
        raise


# Module-level singleton.
gemini_provider = GeminiProvider()
