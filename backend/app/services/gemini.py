from __future__ import annotations

import json
from typing import Any

from google import genai
from google.genai import types

from ..config import settings
from .circuit_breakers import gemini_breaker

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


@gemini_breaker
async def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    client = get_client()
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(task_type=task_type),
    )
    return result.embeddings[0].values


@gemini_breaker
async def generate_structured(
    prompt: str,
    schema_hint: str = "",
    model: str = "gemini-2.5-flash",
) -> dict[str, Any]:
    """Call Gemini and return a parsed JSON dict.

    ``model`` defaults to Flash for latency/cost; callers that need the
    Pro variant (e.g., STORM section synthesis) pass ``model="gemini-2.5-pro"``.
    """
    client = get_client()
    system_instruction = "You are an expert data extraction assistant. Return valid JSON only."
    if schema_hint:
        system_instruction += f"\n\nExpected output schema:\n{schema_hint}"

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )
    text = response.text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
        raise


@gemini_breaker
async def generate_text(prompt: str, system: str = "", model: str = "gemini-2.5-flash") -> str:
    client = get_client()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system or "You are a helpful AI assistant.",
            temperature=0.7,
        ),
    )
    return response.text
