"""Exa search tool for expert agents.

Calls are cached via ``core.tool_cache`` keyed on (query, num_results, type).
Without the cache, two missions on overlapping topics — common during
research crew runs — pay Exa twice for identical searches. Default TTL is
1 hour because Exa results don't shift meaningfully on shorter horizons.
"""
from __future__ import annotations

from typing import Any

import httpx

from ....config import settings
from ....core.tool_cache import tool_cache

TOOL_NAME = "exa_search"
_CACHE_TTL_SECONDS = 3600

TOOL_SCHEMA: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": (
        "Search the web using Exa's neural search API. Returns relevant URLs "
        "with content snippets. Results are cached for 1 hour."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (1-10)",
                "default": 5,
            },
            "type": {
                "type": "string",
                "description": "Search type: keyword or neural",
                "enum": ["keyword", "neural"],
                "default": "neural",
            },
        },
        "required": ["query"],
    },
}


async def _fetch(query: str, num_results: int, search_type: str) -> dict[str, Any]:
    """Real Exa API call. Wrapped by the cache layer."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.exa.ai/search",
            headers={
                "x-api-key": settings.exa_api_key,
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "numResults": min(num_results, 10),
                "type": search_type,
                "contents": {"text": {"maxCharacters": 1000}},
            },
        )
        response.raise_for_status()
        data = response.json()

    results = [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("text", "")[:500],
            "score": r.get("score", 0),
        }
        for r in data.get("results", [])
    ]
    return {
        "tool": TOOL_NAME,
        "query": query,
        "results": results,
        "count": len(results),
        "status": "success",
    }


async def execute(
    query: str,
    num_results: int = 5,
    type: str = "neural",  # noqa: A002 - matches schema; renamed to search_type internally
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute an Exa search with result caching."""
    if not settings.exa_api_key:
        return {
            "tool": TOOL_NAME,
            "query": query,
            "error": "EXA_API_KEY not configured",
            "status": "error",
        }

    params = {"query": query, "num_results": min(num_results, 10), "type": type}

    try:
        return await tool_cache.cached(
            TOOL_NAME,
            params,
            _CACHE_TTL_SECONDS,
            lambda: _fetch(query, num_results, type),
        )
    except Exception as exc:
        return {
            "tool": TOOL_NAME,
            "query": query,
            "error": str(exc),
            "status": "error",
        }
