"""Zillow real estate data connector via RapidAPI.

Falls back to mock data when no API key is configured.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from ..base_connector import SourceResult


_RAPIDAPI_HOST = "zillow-com1.p.rapidapi.com"
_SEARCH_URL = f"https://{_RAPIDAPI_HOST}/propertyExtendedSearch"
_PROPERTY_URL = f"https://{_RAPIDAPI_HOST}/property"

_MOCK_LISTINGS = [
    {
        "zpid": "mock-1",
        "address": "123 Mock St, Austin, TX 78701",
        "price": 450_000,
        "beds": 3,
        "baths": 2,
        "sqft": 1_800,
        "property_type": "house",
        "status": "for_sale",
        "url": "https://www.zillow.com/homedetails/mock-1",
    },
    {
        "zpid": "mock-2",
        "address": "456 Sample Ave, Austin, TX 78702",
        "price": 625_000,
        "beds": 4,
        "baths": 3,
        "sqft": 2_400,
        "property_type": "house",
        "status": "for_sale",
        "url": "https://www.zillow.com/homedetails/mock-2",
    },
    {
        "zpid": "mock-3",
        "address": "789 Demo Blvd, Austin, TX 78703",
        "price": 320_000,
        "beds": 2,
        "baths": 1,
        "sqft": 1_100,
        "property_type": "condo",
        "status": "for_sale",
        "url": "https://www.zillow.com/homedetails/mock-3",
    },
]


class ZillowConnector:
    """Real estate data via RapidAPI Zillow endpoint."""

    name: str = "Zillow"
    provider: str = "zillow"
    description: str = (
        "Search real estate listings on Zillow. Returns property details "
        "including price, beds, baths, and square footage."
    )

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @property
    def _has_key(self) -> bool:
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        return {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": _RAPIDAPI_HOST,
        }

    @staticmethod
    def _normalize_listing(raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "zpid": str(raw.get("zpid", "")),
            "address": raw.get("address", raw.get("streetAddress", "")),
            "price": raw.get("price", raw.get("unformattedPrice")),
            "beds": raw.get("bedrooms", raw.get("beds")),
            "baths": raw.get("bathrooms", raw.get("baths")),
            "sqft": raw.get("livingArea", raw.get("sqft")),
            "property_type": raw.get("homeType", raw.get("property_type", "")),
            "status": raw.get("homeStatus", raw.get("status", "")),
            "url": raw.get("detailUrl", raw.get("url", "")),
        }

    # ------------------------------------------------------------------
    # core interface
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        location: str | None = None,
        price_min: int | None = None,
        price_max: int | None = None,
        beds_min: int | None = None,
        property_type: str | None = None,
        status: str = "for_sale",
        **kwargs: Any,
    ) -> SourceResult:
        if not self._has_key:
            return self._mock_search(query, price_min, price_max, beds_min, property_type)

        params: dict[str, Any] = {"location": location or query, "status_type": status}
        if price_min is not None:
            params["minPrice"] = price_min
        if price_max is not None:
            params["maxPrice"] = price_max
        if beds_min is not None:
            params["bedsMin"] = beds_min
        if property_type is not None:
            params["home_type"] = property_type

        response = await self._client.get(_SEARCH_URL, headers=self._headers(), params=params)
        response.raise_for_status()
        body = response.json()

        results_raw = body.get("props", [])
        listings = [self._normalize_listing(r) for r in results_raw]

        return SourceResult(
            data=listings,
            raw_response=body,
            total_results=body.get("totalResultCount", len(listings)),
            source_name=self.name,
            source_url=f"https://www.zillow.com/homes/{query.replace(' ', '-')}",
        )

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        if not self._has_key:
            match = next((m for m in _MOCK_LISTINGS if m["zpid"] == identifier), None)
            data = [match] if match else []
            return SourceResult(
                data=data,
                raw_response=None,
                total_results=len(data),
                source_name=self.name,
                metadata={"mock": True, "warning": "No API key — using mock data"},
            )

        params: dict[str, str] = {}
        if identifier.startswith("http"):
            params["property_url"] = identifier
        else:
            params["zpid"] = identifier

        response = await self._client.get(_PROPERTY_URL, headers=self._headers(), params=params)
        response.raise_for_status()
        body = response.json()

        listing = self._normalize_listing(body)
        return SourceResult(
            data=[listing],
            raw_response=body,
            total_results=1,
            source_name=self.name,
            source_url=listing.get("url"),
        )

    async def get_comps(
        self,
        address: str,
        radius_miles: int = 1,
    ) -> SourceResult:
        """Return comparable properties near *address*."""
        if not self._has_key:
            return SourceResult(
                data=_MOCK_LISTINGS[:2],
                raw_response=None,
                total_results=2,
                source_name=self.name,
                metadata={"mock": True, "warning": "No API key — using mock data"},
            )

        params = {"address": address, "radius": str(radius_miles)}
        response = await self._client.get(
            f"https://{_RAPIDAPI_HOST}/similarProperty",
            headers=self._headers(),
            params=params,
        )
        response.raise_for_status()
        body = response.json()

        comps = body if isinstance(body, list) else body.get("props", [])
        listings = [self._normalize_listing(c) for c in comps]

        return SourceResult(
            data=listings,
            raw_response=body,
            total_results=len(listings),
            source_name=self.name,
            metadata={"radius_miles": radius_miles},
        )

    async def health_check(self) -> dict[str, Any]:
        if not self._has_key:
            return {
                "status": "degraded",
                "latency_ms": 0,
                "message": "No API key configured — mock mode only",
            }

        start = time.monotonic()
        try:
            response = await self._client.get(
                _SEARCH_URL,
                headers=self._headers(),
                params={"location": "Austin, TX"},
            )
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
            "name": "zillow_search",
            "description": (
                "Search real estate listings. Returns property details "
                "including price, beds, baths, sqft."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Property search query or address",
                    },
                    "location": {"type": "string"},
                    "price_min": {"type": "integer"},
                    "price_max": {"type": "integer"},
                    "beds_min": {"type": "integer"},
                    "property_type": {
                        "type": "string",
                        "enum": [
                            "house",
                            "condo",
                            "townhouse",
                            "multi_family",
                            "land",
                        ],
                    },
                },
                "required": ["query"],
            },
        }

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------

    def _mock_search(
        self,
        query: str,
        price_min: int | None,
        price_max: int | None,
        beds_min: int | None,
        property_type: str | None,
    ) -> SourceResult:
        filtered = list(_MOCK_LISTINGS)
        if price_min is not None:
            filtered = [l for l in filtered if (l.get("price") or 0) >= price_min]
        if price_max is not None:
            filtered = [l for l in filtered if (l.get("price") or 0) <= price_max]
        if beds_min is not None:
            filtered = [l for l in filtered if (l.get("beds") or 0) >= beds_min]
        if property_type is not None:
            filtered = [l for l in filtered if l.get("property_type") == property_type]

        return SourceResult(
            data=filtered,
            raw_response=None,
            total_results=len(filtered),
            source_name=self.name,
            metadata={"mock": True, "warning": "No API key — returning mock data"},
        )
