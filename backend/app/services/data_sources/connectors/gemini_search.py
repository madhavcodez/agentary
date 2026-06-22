"""Gemini Search connector — wraps the existing gemini_search research module.

Uses Gemini with Google Search grounding to perform real-time web searches
and return structured results via the SourceConnector protocol.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from google import genai
from google.genai import types

from ....config import settings
from ..base_connector import SourceResult

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


class GeminiSearchConnector:
    """Data source connector for Google Search via Gemini AI."""

    name: str = "Gemini Search"
    provider: str = "gemini_search"
    description: str = (
        "Search the web using Google Search via Gemini AI. "
        "Returns real-time web results with snippets."
    )

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        """Search the web using Gemini with Google Search grounding.

        Args:
            query: Search query string.
            **kwargs: Optional ``num_results`` (int, default 10).

        Returns:
            SourceResult with search hits.
        """
        num_results = kwargs.get("num_results", 10)

        if not settings.gemini_api_key:
            logger.warning("Gemini API key not configured; returning empty results")
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": "API key not configured"},
            )

        client = _get_client()

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.3,
                ),
            )

            results: list[dict[str, Any]] = []
            raw_text = (response.text or "").strip()

            # Extract grounding chunks (URLs + titles) from the response
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                grounding_metadata = getattr(candidate, "grounding_metadata", None)
                if grounding_metadata:
                    chunks = getattr(grounding_metadata, "grounding_chunks", None)
                    if chunks:
                        for chunk in chunks:
                            web = getattr(chunk, "web", None)
                            if web and hasattr(web, "uri") and web.uri:
                                results.append(
                                    {
                                        "url": web.uri,
                                        "title": getattr(web, "title", "") or "",
                                        "snippet": "",
                                        "source": "gemini_search",
                                    }
                                )

            # If no grounding chunks, return the raw text as a single result
            if not results and raw_text:
                results.append(
                    {
                        "url": None,
                        "title": "Gemini Search Result",
                        "snippet": raw_text[:2000],
                        "source": "gemini_search",
                    }
                )

            # Trim to requested count
            results = results[:num_results]

            return SourceResult(
                data=results,
                raw_response=raw_text,
                total_results=len(results),
                source_name=self.name,
                metadata={"query": query, "num_results": num_results},
            )

        except Exception as e:
            logger.error("Gemini search failed for query '%s': %s", query, e)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(e), "query": query},
            )

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        """Delegate to gemini_research for detailed company research.

        Args:
            identifier: Company name to research.
            **kwargs: Optional ``role`` (str) for context.

        Returns:
            SourceResult wrapping the research dict.
        """
        from ...research.gemini_search import gemini_research

        role = kwargs.get("role", "")
        try:
            research_data = await gemini_research(identifier, role)
            return SourceResult(
                data=[research_data],
                raw_response=research_data,
                total_results=1,
                source_name=self.name,
                metadata={"company": identifier, "role": role},
            )
        except Exception as e:
            logger.error("Gemini research failed for '%s': %s", identifier, e)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(e), "company": identifier},
            )

    async def health_check(self) -> dict[str, Any]:
        """Ping the Gemini API with a minimal request.

        Returns:
            Dict with ``status``, ``latency_ms``, and ``message``.
        """
        if not settings.gemini_api_key:
            return {
                "status": "down",
                "latency_ms": 0,
                "message": "Gemini API key not configured",
            }

        client = _get_client()
        start = time.time()
        try:
            client.models.generate_content(
                model="gemini-2.5-flash",
                contents="ping",
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=5,
                ),
            )
            latency = round((time.time() - start) * 1000, 1)
            return {
                "status": "healthy",
                "latency_ms": latency,
                "message": "Gemini API responding",
            }
        except Exception as e:
            latency = round((time.time() - start) * 1000, 1)
            return {
                "status": "down",
                "latency_ms": latency,
                "message": f"Gemini API error: {e}",
            }

    def get_tool_definition(self) -> dict[str, Any]:
        """Return Gemini function-calling compatible tool definition."""
        return {
            "name": "gemini_search",
            "description": (
                "Search the web using Google Search via Gemini AI. "
                "Returns real-time web results with snippets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "num_results": {
                        "type": "integer",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        }
