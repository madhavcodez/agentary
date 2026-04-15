"""ATTOM Data property detail connector.

Fetches lot size, building footprint, year built, stories, and dimensions
for a given address. Falls back to deterministic mock data (plausible for
Plano, TX) when no API key is configured.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx

from ..base_connector import SourceResult


_BASE_URL = "https://api.gateway.attomdata.com/propertyapi/v1.0.0"
_DETAIL_PATH = "/property/detail"


class AttomConnector:
    """Property detail records via the ATTOM Data API."""

    name: str = "ATTOM"
    provider: str = "attom"
    description: str = (
        "Retrieve property detail records (lot size, building footprint, "
        "year built, stories) from ATTOM Data."
    )

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            timeout=30.0,
            base_url=_BASE_URL,
            headers={
                "accept": "application/json",
                "apikey": api_key or "",
            },
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    # Audit fix (code-review HIGH #2): the underlying ``httpx.AsyncClient``
    # was never closed, leaking a pooled connection per mission run. Add
    # an explicit ``aclose`` plus async-context-manager hooks so callers
    # can ``async with AttomConnector(...) as attom:`` and get automatic
    # cleanup.
    async def aclose(self) -> None:
        """Close the underlying HTTPX client (idempotent)."""
        await self._client.aclose()

    async def __aenter__(self) -> "AttomConnector":
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
    def _split_address(address: str) -> tuple[str, str]:
        """Split a one-line address into (address1, address2) halves.

        ATTOM expects address1 = street portion, address2 = city/state/zip.
        """
        parts = [p.strip() for p in address.split(",")]
        if len(parts) >= 2:
            return parts[0], ", ".join(parts[1:])
        return address, ""

    @staticmethod
    def _normalize_detail(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize ATTOM's nested payload to the flat Pool Concierge shape."""
        prop = (raw.get("property") or [{}])[0] if raw.get("property") else {}
        lot = prop.get("lot", {}) or {}
        building = prop.get("building", {}) or {}
        summary = prop.get("summary", {}) or {}
        size_block = building.get("size", {}) or {}
        rooms_block = building.get("rooms", {}) or {}

        lot_size_sqft = lot.get("lotsize2") or lot.get("lotSize2") or lot.get("lotSize1")
        building_sqft = (
            size_block.get("bldgsize")
            or size_block.get("universalsize")
            or size_block.get("livingsize")
        )
        year_built = summary.get("yearbuilt") or summary.get("yearBuilt")
        stories = rooms_block.get("storynum") or rooms_block.get("stories")
        lot_depth = lot.get("depth")
        lot_frontage = lot.get("frontage")

        return {
            "lot_size_sqft": float(lot_size_sqft) if lot_size_sqft else None,
            "lot_dimensions": (
                f"{lot_frontage}x{lot_depth}"
                if (lot_frontage and lot_depth)
                else None
            ),
            "building_footprint_sqft": (
                float(building_sqft) if building_sqft else None
            ),
            "year_built": int(year_built) if year_built else None,
            "stories": float(stories) if stories else None,
        }

    def _mock_detail(self, address: str) -> dict[str, Any]:
        """Deterministic plausible Plano TX property detail keyed on address."""
        digest = hashlib.sha256(address.encode("utf-8")).digest()
        # Map digest bytes to plausible ranges for Plano TX SFH.
        lot_size = 7_500 + (digest[0] % 60) * 125  # 7,500 – 14,875 sqft
        frontage = 60 + (digest[1] % 25)  # 60 – 84 ft
        depth = max(90, lot_size // max(frontage, 1))  # derive depth
        footprint = 1_800 + (digest[2] % 40) * 40  # 1,800 – 3,360 sqft
        year_built = 1985 + (digest[3] % 35)  # 1985 – 2019
        stories = 1.0 if digest[4] % 2 == 0 else 2.0
        return {
            "lot_size_sqft": float(lot_size),
            "lot_dimensions": f"{frontage}x{depth}",
            "building_footprint_sqft": float(footprint),
            "year_built": int(year_built),
            "stories": stories,
        }

    # ------------------------------------------------------------------
    # core interface
    # ------------------------------------------------------------------

    async def get_property_detail(self, address: str) -> SourceResult:
        """Fetch property detail for *address*.

        Returns a ``SourceResult`` whose ``data[0]`` dict contains the
        normalized Pool Concierge fields. Falls back to mock data when
        no API key is configured.
        """
        if not self._has_key:
            detail = self._mock_detail(address)
            return SourceResult(
                data=[detail],
                raw_response=None,
                total_results=1,
                source_name=self.name,
                metadata={
                    "mock": True,
                    "warning": "No API key — using mock property detail",
                    "address": address,
                },
            )

        address1, address2 = self._split_address(address)
        params: dict[str, Any] = {"address1": address1, "address2": address2}
        response = await self._client.get(_DETAIL_PATH, params=params)
        response.raise_for_status()
        body = response.json()

        detail = self._normalize_detail(body)
        return SourceResult(
            data=[detail],
            raw_response=body,
            total_results=1,
            source_name=self.name,
            metadata={"address": address},
        )

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        """SourceConnector compatibility — treat *query* as an address."""
        return await self.get_property_detail(query)

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        return await self.get_property_detail(identifier)

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
                _DETAIL_PATH,
                params={"address1": "1600 Amphitheatre Pkwy", "address2": "Mountain View, CA"},
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
            "name": "attom_property_detail",
            "description": (
                "Fetch property detail (lot size, building footprint, "
                "year built, stories) for an address."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Full US address, e.g. '123 Main St, Plano, TX 75024'",
                    },
                },
                "required": ["address"],
            },
        }
