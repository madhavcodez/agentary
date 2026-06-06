"""Unified Exa adapter.

Single import point for every Exa call in the codebase. Three previous
wrappers (in ``services/crews/tools/``, ``services/data_sources/connectors/``,
``services/research/``) now defer to this module.

Design choices
- ``ExaSearchResult`` is a typed dataclass — callers don't depend on the
  SDK's response shape, so an Exa SDK upgrade lands here only.
- Client is lazy-instantiated to keep import-time cheap; missing API key
  surfaces as ``ExaUnavailable`` so callers can branch instead of falling
  back to opaque ``None``.
- The circuit breaker that previously gated only the research/contact
  pipeline now wraps every Exa call here. Burnout is uniform.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from exa_py import Exa

from ....config import settings
from ....services.circuit_breakers import exa_breaker

logger = logging.getLogger(__name__)


class ExaUnavailable(RuntimeError):
    """Raised when EXA_API_KEY is unset or the client cannot be built."""


@dataclass(frozen=True)
class ExaSearchResult:
    """One result row from an Exa search."""

    url: str
    title: str
    snippet: str
    score: float | None = None
    published_date: str | None = None
    raw: Any = field(default=None, repr=False, compare=False)


class ExaProvider:
    """Adapter over the Exa SDK with a stable, documented interface."""

    def __init__(self) -> None:
        self._client: Exa | None = None

    def _ensure_client(self) -> Exa:
        if self._client is None:
            if not settings.exa_api_key:
                raise ExaUnavailable("EXA_API_KEY not configured")
            self._client = Exa(api_key=settings.exa_api_key)
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(settings.exa_api_key)

    @exa_breaker
    async def search(
        self,
        query: str,
        *,
        num_results: int = 10,
        search_type: str = "auto",
        include_text: bool = True,
        max_text_chars: int = 1000,
    ) -> list[ExaSearchResult]:
        """Run a search and return typed results.

        ``search_type`` is one of ``keyword``, ``neural``, or ``auto``.
        ``include_text`` requests page content snippets up to
        ``max_text_chars`` per result.
        """
        client = self._ensure_client()

        # The SDK has changed signature across versions; we pass the kwargs
        # the current pin understands and let the SDK reject anything else.
        kwargs: dict[str, Any] = {
            "num_results": min(max(num_results, 1), 10),
            "type": search_type,
        }
        if include_text:
            try:
                response = client.search_and_contents(
                    query,
                    text={"max_characters": max_text_chars},
                    **kwargs,
                )
            except (AttributeError, TypeError):
                # Older SDK paths fall back to search without contents.
                response = client.search(query, **kwargs)
        else:
            response = client.search(query, **kwargs)

        results: list[ExaSearchResult] = []
        for r in getattr(response, "results", []):
            text_attr = getattr(r, "text", None) or ""
            results.append(
                ExaSearchResult(
                    url=getattr(r, "url", ""),
                    title=getattr(r, "title", "") or "",
                    snippet=text_attr[:max_text_chars],
                    score=getattr(r, "score", None),
                    published_date=getattr(r, "published_date", None),
                    raw=r,
                )
            )
        return results

    @exa_breaker
    async def get_contents(
        self, urls: list[str], *, max_text_chars: int = 5000
    ) -> list[ExaSearchResult]:
        """Fetch full content for an explicit list of URLs."""
        client = self._ensure_client()
        response = client.get_contents(urls)
        results: list[ExaSearchResult] = []
        for r in getattr(response, "results", []):
            text_attr = getattr(r, "text", "") or ""
            results.append(
                ExaSearchResult(
                    url=getattr(r, "url", ""),
                    title=getattr(r, "title", "") or "",
                    snippet=text_attr[:max_text_chars],
                    score=None,
                    published_date=getattr(r, "published_date", None),
                    raw=r,
                )
            )
        return results

    async def health_check(self) -> dict[str, Any]:
        """One-shot keyword query to confirm reachability."""
        if not self.is_configured:
            return {
                "status": "down",
                "latency_ms": 0,
                "message": "EXA_API_KEY not configured",
            }
        start = time.time()
        try:
            await self.search("ping", num_results=1, search_type="keyword")
            return {
                "status": "healthy",
                "latency_ms": round((time.time() - start) * 1000, 1),
                "message": "Exa API responding",
            }
        except Exception as exc:
            return {
                "status": "down",
                "latency_ms": round((time.time() - start) * 1000, 1),
                "message": f"Exa API error: {exc}",
            }


# Module-level singleton — same lifetime as the process.
exa_provider = ExaProvider()
