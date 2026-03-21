"""Exa search tool for expert agents."""
from __future__ import annotations

from typing import Any

import httpx

from ....config import settings

TOOL_SCHEMA: dict[str, Any] = {
    "name": "exa_search",
    "description": "Search the web using Exa's neural search API. Returns relevant URLs with content snippets.",
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


async def execute(
    query: str, num_results: int = 5, type: str = "neural", **kwargs: Any
) -> dict[str, Any]:
    """Execute an Exa search."""
    if not settings.exa_api_key:
        return {
            "tool": "exa_search",
            "query": query,
            "error": "EXA_API_KEY not configured",
            "status": "error",
        }

    try:
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
                    "type": type,
                    "contents": {"text": {"maxCharacters": 1000}},
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for r in data.get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("text", "")[:500],
                    "score": r.get("score", 0),
                })

            return {
                "tool": "exa_search",
                "query": query,
                "results": results,
                "count": len(results),
                "status": "success",
            }
    except Exception as e:
        return {
            "tool": "exa_search",
            "query": query,
            "error": str(e),
            "status": "error",
        }
