"""Gemini-powered web search tool for expert agents."""
from __future__ import annotations

from typing import Any

from ...gemini import generate_text

TOOL_SCHEMA: dict[str, Any] = {
    "name": "gemini_search",
    "description": "Search the web using Gemini's built-in knowledge and grounding. Returns a summary with key facts.",
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


async def execute(query: str, focus: str = "facts", **kwargs: Any) -> dict[str, Any]:
    """Execute a Gemini-powered search."""
    system = (
        f"You are a search engine. The user wants {focus} about the following topic. "
        "Return a structured JSON response with: "
        '{"results": [{"title": "...", "snippet": "...", "url": "...", "relevance": 0.0-1.0}], '
        '"summary": "brief overview"}'
    )
    prompt = f"Search for: {query}"

    try:
        result = await generate_text(prompt, system=system)
        return {
            "tool": "gemini_search",
            "query": query,
            "focus": focus,
            "result": result,
            "status": "success",
        }
    except Exception as e:
        return {
            "tool": "gemini_search",
            "query": query,
            "error": str(e),
            "status": "error",
        }
