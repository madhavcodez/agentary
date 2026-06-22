"""Gemini-powered web search tool for expert agents.

Cached for 1 hour via ``core.tool_cache``. Gemini grounding calls are paid;
two missions on the same topic shouldn't both burn quota.
"""

from __future__ import annotations

from typing import Any

from ....core.tool_cache import tool_cache
from ...gemini import generate_text

TOOL_NAME = "gemini_search"
_CACHE_TTL_SECONDS = 3600

TOOL_SCHEMA: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": (
        "Search the web using Gemini's built-in knowledge and grounding. "
        "Returns a summary with key facts. Results are cached for 1 hour."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up",
            },
            "focus": {
                "type": "string",
                "description": "What aspect to focus on: facts, statistics, news, opinions",
                "enum": ["facts", "statistics", "news", "opinions"],
            },
        },
        "required": ["query"],
    },
}


async def _fetch(query: str, focus: str) -> dict[str, Any]:
    system = (
        f"You are a search engine. The user wants {focus} about the following topic. "
        "Return a structured JSON response with: "
        '{"results": [{"title": "...", "snippet": "...", "url": "...", "relevance": 0.0-1.0}], '
        '"summary": "brief overview"}'
    )
    prompt = f"Search for: {query}"
    result = await generate_text(prompt, system=system)
    return {
        "tool": TOOL_NAME,
        "query": query,
        "focus": focus,
        "result": result,
        "status": "success",
    }


async def execute(query: str, focus: str = "facts", **kwargs: Any) -> dict[str, Any]:
    """Execute a Gemini-powered search with result caching."""
    params = {"query": query, "focus": focus}
    try:
        return await tool_cache.cached(
            TOOL_NAME,
            params,
            _CACHE_TTL_SECONDS,
            lambda: _fetch(query, focus),
        )
    except Exception as exc:
        return {
            "tool": TOOL_NAME,
            "query": query,
            "error": str(exc),
            "status": "error",
        }
