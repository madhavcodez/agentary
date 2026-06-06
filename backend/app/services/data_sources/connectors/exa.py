"""Exa data-source connector — wraps the unified Exa provider.

Previously this module duplicated the SDK access seen in two other places.
Now it implements the ``SourceConnector`` protocol on top of the canonical
``ExaProvider`` so business code goes through one Exa surface only.
"""
from __future__ import annotations

import logging
from typing import Any

from ....platform.infrastructure.providers import exa_provider
from ....platform.infrastructure.providers.exa import ExaUnavailable
from ..base_connector import SourceResult

logger = logging.getLogger(__name__)


class ExaConnector:
    """Data-source connector for the Exa semantic search engine."""

    name: str = "exa_search"
    provider: str = "exa"
    description: str = (
        "Semantic search engine. Find relevant web pages using neural search."
    )

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        """Search via Exa, returning a ``SourceResult`` envelope."""
        num_results = kwargs.get("num_results", 10)
        search_type = kwargs.get("type", "auto")

        try:
            results = await exa_provider.search(
                query,
                num_results=num_results,
                search_type=search_type,
                include_text=True,
            )
        except ExaUnavailable as exc:
            logger.warning("Exa unavailable: %s", exc)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(exc)},
            )
        except Exception as exc:
            logger.error("Exa search failed for '%s': %s", query, exc)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(exc), "query": query},
            )

        data = [
            {
                "url": r.url,
                "title": r.title,
                "snippet": r.snippet,
                "score": r.score,
                "published_date": r.published_date,
                "source": "exa",
            }
            for r in results
        ]
        return SourceResult(
            data=data,
            raw_response=[r.raw for r in results],
            total_results=len(data),
            source_name=self.name,
            metadata={
                "query": query,
                "num_results": num_results,
                "type": search_type,
            },
        )

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        """Fetch content for a specific URL via Exa."""
        try:
            results = await exa_provider.get_contents([identifier])
        except ExaUnavailable as exc:
            logger.warning("Exa unavailable: %s", exc)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(exc)},
            )
        except Exception as exc:
            logger.error("Exa get_contents failed for '%s': %s", identifier, exc)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(exc), "url": identifier},
            )

        data = [
            {
                "url": r.url,
                "title": r.title,
                "text": r.snippet,
                "source": "exa",
            }
            for r in results
        ]
        return SourceResult(
            data=data,
            raw_response=[r.raw for r in results],
            total_results=len(data),
            source_name=self.name,
            source_url=identifier,
            metadata={"url": identifier},
        )

    async def health_check(self) -> dict[str, Any]:
        return await exa_provider.health_check()

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "name": "exa_search",
            "description": (
                "Semantic search engine. Find relevant web pages using neural search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "num_results": {"type": "integer", "default": 10},
                    "type": {
                        "type": "string",
                        "enum": ["keyword", "neural", "auto"],
                        "default": "auto",
                    },
                },
                "required": ["query"],
            },
        }
