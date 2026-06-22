"""Crunchbase company/startup data connector.

Uses the Crunchbase v4 API (autocompletes for search, entity lookup
for details). Falls back to RapidAPI if that endpoint is configured.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from ..base_connector import SourceResult

_AUTOCOMPLETE_URL = "https://api.crunchbase.com/api/v4/autocompletes"
_ENTITY_URL = "https://api.crunchbase.com/api/v4/entities/organizations"


class CrunchbaseConnector:
    """Company and startup data via the Crunchbase API."""

    name: str = "Crunchbase"
    provider: str = "crunchbase"
    description: str = (
        "Search for companies and startups. Returns funding, leadership, "
        "and industry information."
    )

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_company(raw: dict[str, Any]) -> dict[str, Any]:
        props = raw.get("properties", raw)
        identifier = raw.get("identifier", {})
        return {
            "name": (
                identifier.get("value")
                or props.get("name")
                or props.get("short_description", "")
            ),
            "slug": identifier.get("permalink", props.get("permalink", "")),
            "short_description": props.get("short_description", ""),
            "homepage_url": props.get("homepage_url"),
            "founded_on": props.get("founded_on"),
            "location": props.get("location_identifiers", props.get("location")),
            "num_employees": props.get("num_employees_enum"),
            "funding_total_usd": props.get("funding_total", {}).get("value_usd")
            if isinstance(props.get("funding_total"), dict)
            else props.get("funding_total"),
            "last_funding_type": props.get("last_funding_type"),
            "categories": [
                c.get("value", c) if isinstance(c, dict) else c
                for c in (props.get("categories", []) or [])
            ],
            "crunchbase_url": (
                f"https://www.crunchbase.com/organization/"
                f"{identifier.get('permalink', props.get('permalink', ''))}"
            ),
        }

    def _base_params(self) -> dict[str, str]:
        return {"user_key": self._api_key}

    # ------------------------------------------------------------------
    # core interface
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        industry: str | None = None,
        location: str | None = None,
        funding_min: int | None = None,
        **kwargs: Any,
    ) -> SourceResult:
        params: dict[str, Any] = {
            **self._base_params(),
            "query": query,
            "collection_ids": "organizations",
            "limit": 25,
        }

        response = await self._client.get(_AUTOCOMPLETE_URL, params=params)
        response.raise_for_status()
        body = response.json()

        entities = body.get("entities", [])
        companies = [self._normalize_company(e) for e in entities]

        # Client-side filters (autocomplete API has limited server filtering)
        if industry is not None:
            industry_lower = industry.lower()
            companies = [
                c
                for c in companies
                if any(industry_lower in cat.lower() for cat in c.get("categories", []))
            ]
        if location is not None:
            location_lower = location.lower()
            companies = [
                c
                for c in companies
                if location_lower in str(c.get("location", "")).lower()
            ]
        if funding_min is not None:
            companies = [
                c
                for c in companies
                if (c.get("funding_total_usd") or 0) >= funding_min
            ]

        return SourceResult(
            data=companies,
            raw_response=body,
            total_results=len(companies),
            source_name=self.name,
            source_url=f"https://www.crunchbase.com/textsearch?q={query}",
        )

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        """Get company details by Crunchbase slug (permalink)."""
        url = f"{_ENTITY_URL}/{identifier}"
        response = await self._client.get(url, params=self._base_params())
        response.raise_for_status()
        body = response.json()

        company = self._normalize_company(body)

        return SourceResult(
            data=[company],
            raw_response=body,
            total_results=1,
            source_name=self.name,
            source_url=company.get("crunchbase_url"),
        )

    async def health_check(self) -> dict[str, Any]:
        start = time.monotonic()
        try:
            params = {**self._base_params(), "query": "test", "limit": 1}
            response = await self._client.get(_AUTOCOMPLETE_URL, params=params)
            latency_ms = round((time.monotonic() - start) * 1_000, 1)
            if response.status_code == 200:
                return {"status": "healthy", "latency_ms": latency_ms, "message": "OK"}
            return {
                "status": "degraded",
                "latency_ms": latency_ms,
                "message": f"HTTP {response.status_code}",
            }
        except Exception as exc:
            latency_ms = round((time.monotonic() - start) * 1_000, 1)
            return {"status": "down", "latency_ms": latency_ms, "message": str(exc)}

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "name": "crunchbase_search",
            "description": (
                "Search for companies and startups. Returns funding, "
                "leadership, industry info."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "industry": {"type": "string"},
                    "location": {"type": "string"},
                    "funding_min": {
                        "type": "integer",
                        "description": "Minimum funding in USD",
                    },
                },
                "required": ["query"],
            },
        }
