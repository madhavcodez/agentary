"""Yelp Fusion API connector.

Searches for local businesses, retrieves details, and fetches reviews.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from ..base_connector import SourceResult

_BASE_URL = "https://api.yelp.com/v3"


class YelpConnector:
    """Local business data via the Yelp Fusion API."""

    name: str = "Yelp"
    provider: str = "yelp"
    description: str = (
        "Search for local businesses on Yelp. Returns ratings, reviews, " "and contact information."
    )

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=30.0,
            base_url=_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_business(raw: dict[str, Any]) -> dict[str, Any]:
        location = raw.get("location", {})
        return {
            "id": raw.get("id", ""),
            "name": raw.get("name", ""),
            "rating": raw.get("rating"),
            "review_count": raw.get("review_count"),
            "price": raw.get("price"),
            "phone": raw.get("display_phone", raw.get("phone", "")),
            "address": ", ".join(location.get("display_address", [])),
            "city": location.get("city"),
            "state": location.get("state"),
            "zip_code": location.get("zip_code"),
            "categories": [c.get("title", "") for c in raw.get("categories", [])],
            "url": raw.get("url", ""),
            "image_url": raw.get("image_url"),
            "coordinates": raw.get("coordinates"),
            "is_closed": raw.get("is_closed"),
        }

    # ------------------------------------------------------------------
    # core interface
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        term: str | None = None,
        location: str | None = None,
        radius: int | None = None,
        categories: str | None = None,
        price: str | None = None,
        sort_by: str = "best_match",
        **kwargs: Any,
    ) -> SourceResult:
        params: dict[str, Any] = {
            "term": term or query,
            "location": location or query,
            "sort_by": sort_by,
        }
        if radius is not None:
            params["radius"] = min(radius, 40_000)  # Yelp max 40 km
        if categories is not None:
            params["categories"] = categories
        if price is not None:
            params["price"] = price

        response = await self._client.get("/businesses/search", params=params)
        response.raise_for_status()
        body = response.json()

        businesses = [self._normalize_business(b) for b in body.get("businesses", [])]

        return SourceResult(
            data=businesses,
            raw_response=body,
            total_results=body.get("total", len(businesses)),
            source_name=self.name,
            source_url=f"https://www.yelp.com/search?find_desc={query}",
        )

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        response = await self._client.get(f"/businesses/{identifier}")
        response.raise_for_status()
        body = response.json()

        business = self._normalize_business(body)

        return SourceResult(
            data=[business],
            raw_response=body,
            total_results=1,
            source_name=self.name,
            source_url=business.get("url"),
        )

    async def get_reviews(
        self,
        business_id: str,
        limit: int = 3,
    ) -> SourceResult:
        """Fetch reviews for a specific business."""
        response = await self._client.get(
            f"/businesses/{business_id}/reviews",
            params={"limit": limit},
        )
        response.raise_for_status()
        body = response.json()

        reviews = [
            {
                "id": r.get("id"),
                "rating": r.get("rating"),
                "text": r.get("text"),
                "time_created": r.get("time_created"),
                "user": r.get("user", {}).get("name"),
            }
            for r in body.get("reviews", [])
        ]

        return SourceResult(
            data=reviews,
            raw_response=body,
            total_results=body.get("total", len(reviews)),
            source_name=self.name,
            metadata={"business_id": business_id},
        )

    async def health_check(self) -> dict[str, Any]:
        start = time.monotonic()
        try:
            response = await self._client.get(
                "/businesses/search",
                params={"term": "coffee", "location": "San Francisco, CA", "limit": 1},
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
            "name": "yelp_search",
            "description": (
                "Search for local businesses on Yelp. Returns ratings, " "reviews, contact info."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term, e.g. 'pizza'",
                    },
                    "location": {
                        "type": "string",
                        "description": "City or address",
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Radius in meters",
                    },
                    "categories": {
                        "type": "string",
                        "description": "Yelp category filter",
                    },
                },
                "required": ["query", "location"],
            },
        }
