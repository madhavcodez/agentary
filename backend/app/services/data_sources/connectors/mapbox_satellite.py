"""Mapbox Static API aerial imagery connector.

Returns a PNG image (bytes) of the satellite tile covering a bbox. Falls
back to a procedurally-generated 1024x1024 white PNG with a green
rectangle when no token is configured.
"""

from __future__ import annotations

import io
import time
from typing import Any

import httpx
from PIL import Image, ImageDraw

from ..base_connector import SourceResult


_STATIC_BASE = (
    "https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static"
)
_DEFAULT_SIZE = (1024, 1024)


class MapboxSatelliteConnector:
    """Satellite imagery via the Mapbox Static API."""

    name: str = "Mapbox Satellite"
    provider: str = "mapbox"
    description: str = (
        "Retrieve aerial / satellite PNG imagery centered on a bounding box."
    )

    def __init__(self, token: str) -> None:
        self._token = token
        self._client = httpx.AsyncClient(timeout=30.0)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    # Audit fix (code-review HIGH #2): close the underlying HTTPX client
    # instead of leaking a connection pool per mission.
    async def aclose(self) -> None:
        """Close the underlying HTTPX client (idempotent)."""
        await self._client.aclose()

    async def __aenter__(self) -> "MapboxSatelliteConnector":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.aclose()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @property
    def _has_key(self) -> bool:
        return bool(self._token)

    @staticmethod
    def _mock_png(size: tuple[int, int] = _DEFAULT_SIZE) -> bytes:
        """Return a deterministic white PNG with a green rectangle."""
        width, height = size
        img = Image.new("RGB", (width, height), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Green rectangle roughly centered — indicates "backyard grass".
        left = int(width * 0.20)
        top = int(height * 0.30)
        right = int(width * 0.80)
        bottom = int(height * 0.85)
        draw.rectangle([left, top, right, bottom], fill=(80, 160, 80))
        # A small brown rectangle for the house footprint near the top.
        house_left = int(width * 0.35)
        house_top = int(height * 0.12)
        house_right = int(width * 0.65)
        house_bottom = int(height * 0.32)
        draw.rectangle(
            [house_left, house_top, house_right, house_bottom],
            fill=(160, 120, 80),
        )
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def _bbox_center(bbox: tuple[float, float, float, float]) -> tuple[float, float]:
        min_lon, min_lat, max_lon, max_lat = bbox
        return (
            (min_lon + max_lon) / 2.0,
            (min_lat + max_lat) / 2.0,
        )

    # ------------------------------------------------------------------
    # core interface
    # ------------------------------------------------------------------

    async def get_aerial_image(
        self,
        bbox: tuple[float, float, float, float],
        *,
        zoom: int = 20,
        size: tuple[int, int] = _DEFAULT_SIZE,
    ) -> SourceResult:
        """Fetch a PNG aerial tile for the given ``bbox``.

        ``bbox`` is ``(min_lon, min_lat, max_lon, max_lat)`` in WGS84 degrees.
        The ``data[0]["image_bytes"]`` slot holds raw PNG bytes.
        """
        width, height = size

        if not self._has_key:
            image_bytes = self._mock_png(size=size)
            return SourceResult(
                data=[{"image_bytes": image_bytes, "format": "png"}],
                raw_response=None,
                total_results=1,
                source_name=self.name,
                metadata={
                    "mock": True,
                    "warning": "No Mapbox token — using synthetic PNG",
                    "bbox": list(bbox),
                    "zoom": zoom,
                },
            )

        center_lon, center_lat = self._bbox_center(bbox)
        path = (
            f"/{center_lon},{center_lat},{zoom},0,0/{width}x{height}"
        )
        url = f"{_STATIC_BASE}{path}"
        response = await self._client.get(
            url,
            params={"access_token": self._token},
        )
        response.raise_for_status()
        image_bytes = response.content

        return SourceResult(
            data=[{"image_bytes": image_bytes, "format": "png"}],
            raw_response=None,
            total_results=1,
            source_name=self.name,
            source_url=url,
            metadata={"bbox": list(bbox), "zoom": zoom},
        )

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        raise NotImplementedError(
            "Use get_aerial_image(bbox) for Mapbox Satellite."
        )

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        raise NotImplementedError(
            "Use get_aerial_image(bbox) for Mapbox Satellite."
        )

    async def health_check(self) -> dict[str, Any]:
        if not self._has_key:
            return {
                "status": "degraded",
                "latency_ms": 0,
                "message": "No token configured — mock mode only",
            }

        start = time.monotonic()
        try:
            response = await self._client.get(
                f"{_STATIC_BASE}/-122.4,37.78,15,0,0/128x128",
                params={"access_token": self._token},
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
            "name": "mapbox_aerial",
            "description": (
                "Fetch a satellite PNG tile for a bounding box."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "[min_lon, min_lat, max_lon, max_lat]",
                    },
                    "zoom": {"type": "integer", "default": 20},
                },
                "required": ["bbox"],
            },
        }
