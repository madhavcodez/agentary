"""Regrid parcel polygon connector.

Retrieves the GeoJSON polygon for a parcel matching an address. Falls
back to a deterministic rectangular polygon centered on a Plano TX
lat/lon when no API key is configured.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx

from ..base_connector import SourceResult


_BASE_URL = "https://app.regrid.com/api/v2"
_PARCELS_PATH = "/parcels/address"

# Plano, TX reference centroid (public coordinate, Legacy Drive area).
_PLANO_CENTER_LAT = 33.0198
_PLANO_CENTER_LON = -96.6989

# Rough degrees per foot at Plano TX latitude (~33 deg N).
_DEG_PER_FT_LAT = 1.0 / 364_000.0
_DEG_PER_FT_LON = 1.0 / 305_000.0


class RegridConnector:
    """Parcel polygon lookup via the Regrid API."""

    name: str = "Regrid"
    provider: str = "regrid"
    description: str = (
        "Retrieve the GeoJSON parcel polygon for a given address."
    )

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=30.0,
            base_url=_BASE_URL,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    # Audit fix (code-review HIGH #2): close the underlying HTTPX client
    # instead of leaking a connection pool per mission.
    async def aclose(self) -> None:
        """Close the underlying HTTPX client (idempotent)."""
        await self._client.aclose()

    async def __aenter__(self) -> "RegridConnector":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.aclose()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @property
    def _has_key(self) -> bool:
        return bool(self._api_key)

    @staticmethod
    def _rectangle_polygon(
        center_lat: float,
        center_lon: float,
        width_ft: float,
        depth_ft: float,
    ) -> dict[str, Any]:
        """Return a GeoJSON Polygon rectangle centered on (lat, lon)."""
        half_lat = (depth_ft / 2.0) * _DEG_PER_FT_LAT
        half_lon = (width_ft / 2.0) * _DEG_PER_FT_LON
        # GeoJSON uses [lon, lat] coordinate order.
        ring = [
            [center_lon - half_lon, center_lat - half_lat],
            [center_lon + half_lon, center_lat - half_lat],
            [center_lon + half_lon, center_lat + half_lat],
            [center_lon - half_lon, center_lat + half_lat],
            [center_lon - half_lon, center_lat - half_lat],
        ]
        return {"type": "Polygon", "coordinates": [ring]}

    def _mock_polygon(self, address: str) -> dict[str, Any]:
        """Deterministic Plano TX rectangle keyed on address hash."""
        digest = hashlib.sha256(address.encode("utf-8")).digest()
        # Offset a few blocks from the Plano center so mock data varies.
        lat_off = ((digest[0] - 128) / 128.0) * 0.01  # ±0.01 deg
        lon_off = ((digest[1] - 128) / 128.0) * 0.01
        width_ft = 60 + (digest[2] % 25)  # 60 – 84 ft
        depth_ft = 120 + (digest[3] % 40)  # 120 – 159 ft
        return self._rectangle_polygon(
            _PLANO_CENTER_LAT + lat_off,
            _PLANO_CENTER_LON + lon_off,
            width_ft=float(width_ft),
            depth_ft=float(depth_ft),
        )

    @staticmethod
    def _extract_polygon(body: dict[str, Any]) -> dict[str, Any] | None:
        """Extract the first parcel Polygon GeoJSON from a Regrid response."""
        parcels = body.get("parcels") or body.get("features") or []
        if not parcels:
            return None
        first = parcels[0]
        geometry = first.get("geometry") if isinstance(first, dict) else None
        if not geometry:
            return None
        geom_type = geometry.get("type")
        if geom_type == "Polygon":
            return geometry
        if geom_type == "MultiPolygon":
            coords = geometry.get("coordinates") or []
            if coords:
                return {"type": "Polygon", "coordinates": coords[0]}
        return None

    # ------------------------------------------------------------------
    # core interface
    # ------------------------------------------------------------------

    async def get_parcel_polygon(self, address: str) -> SourceResult:
        """Return the GeoJSON Polygon parcel geometry for *address*.

        Falls back to a synthetic Plano TX rectangle when no API key is set.
        """
        if not self._has_key:
            polygon = self._mock_polygon(address)
            return SourceResult(
                data=[{"polygon": polygon}],
                raw_response=None,
                total_results=1,
                source_name=self.name,
                metadata={
                    "mock": True,
                    "warning": "No API key — using mock parcel polygon",
                    "address": address,
                },
            )

        params: dict[str, Any] = {"query": address, "token": self._api_key}
        response = await self._client.get(_PARCELS_PATH, params=params)
        response.raise_for_status()
        body = response.json()

        polygon = self._extract_polygon(body)
        data = [{"polygon": polygon}] if polygon else []
        return SourceResult(
            data=data,
            raw_response=body,
            total_results=len(data),
            source_name=self.name,
            metadata={"address": address},
        )

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        return await self.get_parcel_polygon(query)

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        return await self.get_parcel_polygon(identifier)

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
                _PARCELS_PATH,
                params={
                    "query": "1600 Amphitheatre Pkwy, Mountain View, CA",
                    "token": self._api_key,
                },
            )
            latency_ms = round((time.monotonic() - start) * 1_000, 1)
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "latency_ms": latency_ms,
                    "message": "OK",
                }
            return {
                "status": "degraded",
                "latency_ms": latency_ms,
                "message": f"HTTP {response.status_code}",
            }
        except Exception as exc:
            latency_ms = round((time.monotonic() - start) * 1_000, 1)
            return {
                "status": "down",
                "latency_ms": latency_ms,
                "message": str(exc),
            }

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "name": "regrid_parcel_polygon",
            "description": (
                "Fetch the GeoJSON parcel polygon (lot boundary) for an "
                "address."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Full US address",
                    },
                },
                "required": ["address"],
            },
        }
