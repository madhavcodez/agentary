"""Google Places connector — search for local businesses and places.

Uses the Google Places API (New) via httpx to search for businesses,
retrieve details, and fetch reviews. Falls back to mock data when the
API key is not configured.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from ....config import settings
from ..base_connector import SourceResult

logger = logging.getLogger(__name__)

_BASE_URL = "https://places.googleapis.com/v1"
_TIMEOUT = 15.0


def _mock_place(query: str) -> dict[str, Any]:
    """Return a single mock place result for development without an API key."""
    return {
        "place_id": "mock_place_id_001",
        "name": f"Mock Place ({query})",
        "address": "123 Mock Street, Austin, TX 78701",
        "phone": "+1-555-000-0000",
        "rating": 4.2,
        "total_ratings": 42,
        "types": ["establishment"],
        "business_status": "OPERATIONAL",
        "website": "https://example.com",
        "hours": ["Mon-Fri: 9AM-5PM", "Sat-Sun: Closed"],
        "source": "google_places (mock)",
    }


class GooglePlacesConnector:
    """Data source connector for Google Places API (New)."""

    name: str = "google_places"
    provider: str = "google_places"
    description: str = (
        "Search for local businesses and places. Returns names, addresses, "
        "phone numbers, hours, ratings, reviews."
    )

    def _headers(self, field_mask: str) -> dict[str, str]:
        return {
            "X-Goog-Api-Key": settings.google_places_api_key,
            "X-Goog-FieldMask": field_mask,
            "Content-Type": "application/json",
        }

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        """Search for places matching a text query.

        Args:
            query: Search query, e.g. "gas stations near Austin TX".
            **kwargs: Optional ``location`` (str "lat,lng"),
                      ``radius_meters`` (int, default 5000),
                      ``type`` (str, place type filter).

        Returns:
            SourceResult with place data.
        """
        location = kwargs.get("location")
        radius_meters = kwargs.get("radius_meters", 5000)
        place_type = kwargs.get("type")

        if not settings.google_places_api_key:
            logger.warning(
                "Google Places API key not configured; returning mock data"
            )
            mock = _mock_place(query)
            return SourceResult(
                data=[mock],
                raw_response=None,
                total_results=1,
                source_name=self.name,
                metadata={"warning": "Using mock data — API key not configured"},
            )

        field_mask = (
            "places.id,places.displayName,places.formattedAddress,"
            "places.internationalPhoneNumber,places.rating,"
            "places.userRatingCount,places.types,"
            "places.businessStatus,places.websiteUri,"
            "places.currentOpeningHours"
        )

        body: dict[str, Any] = {"textQuery": query}

        if location:
            parts = [p.strip() for p in location.split(",")]
            if len(parts) == 2:
                try:
                    lat, lng = float(parts[0]), float(parts[1])
                    body["locationBias"] = {
                        "circle": {
                            "center": {"latitude": lat, "longitude": lng},
                            "radius": float(radius_meters),
                        }
                    }
                except ValueError:
                    logger.warning("Invalid location format: %s", location)

        if place_type:
            body["includedType"] = place_type

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    f"{_BASE_URL}/places:searchText",
                    headers=self._headers(field_mask),
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()

            places = data.get("places", [])
            results: list[dict[str, Any]] = []
            for place in places:
                display_name = place.get("displayName", {})
                hours_obj = place.get("currentOpeningHours", {})
                weekday_descriptions = hours_obj.get("weekdayDescriptions", [])

                results.append({
                    "place_id": place.get("id", ""),
                    "name": display_name.get("text", ""),
                    "address": place.get("formattedAddress", ""),
                    "phone": place.get("internationalPhoneNumber", ""),
                    "rating": place.get("rating"),
                    "total_ratings": place.get("userRatingCount", 0),
                    "types": place.get("types", []),
                    "business_status": place.get("businessStatus", ""),
                    "website": place.get("websiteUri", ""),
                    "hours": weekday_descriptions,
                    "source": "google_places",
                })

            return SourceResult(
                data=results,
                raw_response=data,
                total_results=len(results),
                source_name=self.name,
                metadata={"query": query, "location": location},
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "Google Places search failed (HTTP %s): %s",
                e.response.status_code,
                e.response.text[:300],
            )
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": f"HTTP {e.response.status_code}",
                    "query": query,
                },
            )
        except Exception as e:
            logger.error("Google Places search failed: %s", e)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(e), "query": query},
            )

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        """Get detailed information for a specific place.

        Args:
            identifier: Google Places place ID.
            **kwargs: Additional parameters (unused).

        Returns:
            SourceResult with detailed place data.
        """
        if not settings.google_places_api_key:
            logger.warning(
                "Google Places API key not configured; returning mock data"
            )
            mock = _mock_place(identifier)
            mock["place_id"] = identifier
            return SourceResult(
                data=[mock],
                raw_response=None,
                total_results=1,
                source_name=self.name,
                metadata={"warning": "Using mock data — API key not configured"},
            )

        field_mask = (
            "id,displayName,formattedAddress,internationalPhoneNumber,"
            "rating,userRatingCount,types,businessStatus,websiteUri,"
            "currentOpeningHours,editorialSummary,reviews"
        )

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BASE_URL}/places/{identifier}",
                    headers=self._headers(field_mask),
                )
                resp.raise_for_status()
                place = resp.json()

            display_name = place.get("displayName", {})
            hours_obj = place.get("currentOpeningHours", {})
            summary = place.get("editorialSummary", {})

            raw_reviews = place.get("reviews", [])
            reviews = [
                {
                    "author": rev.get("authorAttribution", {}).get("displayName", ""),
                    "rating": rev.get("rating"),
                    "text": rev.get("text", {}).get("text", ""),
                    "time": rev.get("relativePublishTimeDescription", ""),
                }
                for rev in raw_reviews[:5]
            ]

            result = {
                "place_id": place.get("id", identifier),
                "name": display_name.get("text", ""),
                "address": place.get("formattedAddress", ""),
                "phone": place.get("internationalPhoneNumber", ""),
                "rating": place.get("rating"),
                "total_ratings": place.get("userRatingCount", 0),
                "types": place.get("types", []),
                "business_status": place.get("businessStatus", ""),
                "website": place.get("websiteUri", ""),
                "hours": hours_obj.get("weekdayDescriptions", []),
                "editorial_summary": summary.get("text", ""),
                "reviews": reviews,
                "source": "google_places",
            }

            return SourceResult(
                data=[result],
                raw_response=place,
                total_results=1,
                source_name=self.name,
                source_url=f"{_BASE_URL}/places/{identifier}",
                metadata={"place_id": identifier},
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "Google Places get failed (HTTP %s): %s",
                e.response.status_code,
                e.response.text[:300],
            )
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": f"HTTP {e.response.status_code}",
                    "place_id": identifier,
                },
            )
        except Exception as e:
            logger.error("Google Places get failed: %s", e)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(e), "place_id": identifier},
            )

    async def get_reviews(
        self, place_id: str, max_reviews: int = 5
    ) -> SourceResult:
        """Get reviews for a specific place.

        Args:
            place_id: Google Places place ID.
            max_reviews: Maximum number of reviews to return (default 5).

        Returns:
            SourceResult with review data.
        """
        if not settings.google_places_api_key:
            logger.warning(
                "Google Places API key not configured; returning mock reviews"
            )
            mock_review = {
                "author": "Mock Reviewer",
                "rating": 4,
                "text": "This is a mock review for development purposes.",
                "time": "a week ago",
            }
            return SourceResult(
                data=[mock_review],
                raw_response=None,
                total_results=1,
                source_name=self.name,
                metadata={"warning": "Using mock data — API key not configured"},
            )

        field_mask = "reviews"

        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.get(
                    f"{_BASE_URL}/places/{place_id}",
                    headers=self._headers(field_mask),
                )
                resp.raise_for_status()
                data = resp.json()

            raw_reviews = data.get("reviews", [])
            reviews: list[dict[str, Any]] = []
            for rev in raw_reviews[:max_reviews]:
                reviews.append({
                    "author": rev.get("authorAttribution", {}).get(
                        "displayName", ""
                    ),
                    "rating": rev.get("rating"),
                    "text": rev.get("text", {}).get("text", ""),
                    "time": rev.get("relativePublishTimeDescription", ""),
                })

            return SourceResult(
                data=reviews,
                raw_response=data,
                total_results=len(reviews),
                source_name=self.name,
                metadata={"place_id": place_id, "max_reviews": max_reviews},
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "Google Places reviews failed (HTTP %s): %s",
                e.response.status_code,
                e.response.text[:300],
            )
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": f"HTTP {e.response.status_code}",
                    "place_id": place_id,
                },
            )
        except Exception as e:
            logger.error("Google Places reviews failed: %s", e)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"error": str(e), "place_id": place_id},
            )

    async def health_check(self) -> dict[str, Any]:
        """Test Google Places API connectivity with a minimal search.

        Returns:
            Dict with ``status``, ``latency_ms``, and ``message``.
        """
        if not settings.google_places_api_key:
            return {
                "status": "degraded",
                "latency_ms": 0,
                "message": "Google Places API key not configured — using mock data",
            }

        field_mask = "places.id"
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                resp = await client.post(
                    f"{_BASE_URL}/places:searchText",
                    headers=self._headers(field_mask),
                    json={"textQuery": "test", "maxResultCount": 1},
                )
                resp.raise_for_status()
            latency = round((time.time() - start) * 1000, 1)
            return {
                "status": "healthy",
                "latency_ms": latency,
                "message": "Google Places API responding",
            }
        except Exception as e:
            latency = round((time.time() - start) * 1000, 1)
            return {
                "status": "down",
                "latency_ms": latency,
                "message": f"Google Places API error: {e}",
            }

    def get_tool_definition(self) -> dict[str, Any]:
        """Return Gemini function-calling compatible tool definition."""
        return {
            "name": "google_places",
            "description": (
                "Search for local businesses and places. Returns names, "
                "addresses, phone numbers, hours, ratings, reviews."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Search query, e.g. 'gas stations near Austin TX'"
                        ),
                    },
                    "location": {
                        "type": "string",
                        "description": "Center point 'lat,lng' or address",
                    },
                    "radius_meters": {
                        "type": "integer",
                        "default": 5000,
                    },
                    "type": {
                        "type": "string",
                        "description": (
                            "Place type: gas_station, restaurant, "
                            "real_estate_agency, etc."
                        ),
                    },
                },
                "required": ["query"],
            },
        }
