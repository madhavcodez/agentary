"""Exa connector — wraps the existing exa_search research module.

Uses the Exa semantic search engine to find relevant web pages
via neural or keyword search, implementing the SourceConnector protocol.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from exa_py import Exa

from ....config import settings
from ..base_connector import SourceResult

logger = logging.getLogger(__name__)


def _get_exa_client() -> Exa:
    return Exa(api_key=settings.exa_api_key)


class ExaConnector:
    """Data source connector for the Exa semantic search engine."""

    name: str = "exa_search"
    provider: str = "exa"
    description: str = "Semantic search engine. Find relevant web pages using neural search."

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        """Search using Exa's neural/keyword/auto search.

        Args:
            query: Search query string.
            **kwargs: Optional ``num_results`` (int, default 10),
                      ``type`` (str, default "auto").

        Returns:
            SourceResult with matching pages.
        """
        num_results = kwargs.get("num_results", 10)
        search_type = kwargs.get("type", "auto")

        if not settings.exa_api_key:
            logger.warning("Exa API key not configured; returning empty results")
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": "API key not configured"},
            )

        exa = _get_exa_client()

        try:
            response = exa.search(
                query,
                num_results=num_results,
                type=search_type,
            )

            results: list[dict[str, Any]] = []
            for r in response.results:
                results.append(
                    {
                        "url": r.url,
                        "title": r.title or "",
                        "snippet": (r.text[:500] if r.text else ""),
                        "score": getattr(r, "score", None),
                        "published_date": getattr(r, "published_date", None),
                        "source": "exa",
                    }
                )

            return SourceResult(
                data=results,
                raw_response=response,
                total_results=len(results),
                source_name=self.name,
                metadata={
                    "query": query,
                    "num_results": num_results,
                    "type": search_type,
                },
            )

        except Exception as e:
            logger.error("Exa search failed for query '%s': %s", query, e)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(e), "query": query},
            )

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        """Fetch content for a specific URL using Exa.

        Args:
            identifier: URL to retrieve content for.
            **kwargs: Additional parameters (unused).

        Returns:
            SourceResult with the page content.
        """
        if not settings.exa_api_key:
            logger.warning("Exa API key not configured; returning empty results")
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": "API key not configured"},
            )

        exa = _get_exa_client()

        try:
            response = exa.get_contents([identifier])

            results: list[dict[str, Any]] = []
            for r in response.results:
                results.append(
                    {
                        "url": r.url,
                        "title": r.title or "",
                        "text": r.text or "",
                        "source": "exa",
                    }
                )

            return SourceResult(
                data=results,
                raw_response=response,
                total_results=len(results),
                source_name=self.name,
                source_url=identifier,
                metadata={"url": identifier},
            )

        except Exception as e:
            logger.error("Exa get_contents failed for '%s': %s", identifier, e)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(e), "url": identifier},
            )

    async def health_check(self) -> dict[str, Any]:
        """Perform a minimal Exa search to verify connectivity.

        Returns:
            Dict with ``status``, ``latency_ms``, and ``message``.
        """
        if not settings.exa_api_key:
            return {
                "status": "down",
                "latency_ms": 0,
                "message": "Exa API key not configured",
            }

        exa = _get_exa_client()
        start = time.time()
        try:
            exa.search("test", num_results=1, type="keyword")
            latency = round((time.time() - start) * 1000, 1)
            return {
                "status": "healthy",
                "latency_ms": latency,
                "message": "Exa API responding",
            }
        except Exception as e:
            latency = round((time.time() - start) * 1000, 1)
            return {
                "status": "down",
                "latency_ms": latency,
                "message": f"Exa API error: {e}",
            }

    def get_tool_definition(self) -> dict[str, Any]:
        """Return Gemini function-calling compatible tool definition."""
        return {
            "name": "exa_search",
            "description": (
                "Semantic search engine. Find relevant web pages " "using neural search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                    },
                    "num_results": {
                        "type": "integer",
                        "default": 10,
                    },
                    "type": {
                        "type": "string",
                        "enum": ["keyword", "neural", "auto"],
                        "default": "auto",
                    },
                },
                "required": ["query"],
            },
        }
