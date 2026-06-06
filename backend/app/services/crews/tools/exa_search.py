"""Exa search tool for expert agents.

Delegates to the unified ``platform.infrastructure.providers.exa`` adapter.
SDK details (retry policy, error handling, response shape) live there;
this module owns the tool-schema definition the LLM sees and translates
typed results into the tool-result dict.
"""
from __future__ import annotations

from typing import Any

from ....platform.infrastructure.providers import exa_provider
from ....platform.infrastructure.providers.exa import ExaUnavailable

TOOL_NAME = "exa_search"

TOOL_SCHEMA: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": (
        "Search the web using Exa's neural search API. Returns relevant URLs "
        "with content snippets."
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
                "description": "Search type: keyword, neural, or auto",
                "enum": ["keyword", "neural", "auto"],
                "default": "neural",
            },
        },
        "required": ["query"],
    },
}


async def execute(
    query: str,
    num_results: int = 5,
    type: str = "neural",  # noqa: A002 - matches schema field name
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute an Exa search via the provider adapter."""
    try:
        results = await exa_provider.search(
            query,
            num_results=num_results,
            search_type=type,
            include_text=True,
            max_text_chars=500,
        )
    except ExaUnavailable as exc:
        return {
            "tool": TOOL_NAME,
            "query": query,
            "error": str(exc),
            "status": "error",
        }
    except Exception as exc:
        return {
            "tool": TOOL_NAME,
            "query": query,
            "error": str(exc),
            "status": "error",
        }

    return {
        "tool": TOOL_NAME,
        "query": query,
        "results": [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
                "score": r.score,
            }
            for r in results
        ],
        "count": len(results),
        "status": "success",
    }
