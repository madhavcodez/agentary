"""County assessor property records connector.

Scrapes public county assessor websites for property data such as
owner name, assessed value, tax amount, and parcel number. MVP
supports Travis/TX, Maricopa/AZ, and Los Angeles/CA.
"""

from __future__ import annotations

from typing import Any

import httpx
from bs4 import BeautifulSoup

from ..base_connector import SourceResult

# ---------------------------------------------------------------------------
# Scraper configs for supported counties
# ---------------------------------------------------------------------------

_COUNTY_CONFIGS: dict[str, dict[str, Any]] = {
    "travis_tx": {
        "label": "Travis County, TX",
        "base_url": "https://propaccess.traviscad.org",
        "search_path": "/clientdb/propertysearch.aspx",
        "search_params": lambda addr: {"sSearch": addr},
        "selectors": {
            "owner": "td.owner-name",
            "assessed_value": "td.assessed-value",
            "tax_amount": "td.tax-amount",
            "parcel": "td.parcel-number",
            "address": "td.property-address",
        },
        "permits_path": None,
    },
    "maricopa_az": {
        "label": "Maricopa County, AZ",
        "base_url": "https://mcassessor.maricopa.gov",
        "search_path": "/mcs.php",
        "search_params": lambda addr: {"q": addr, "search": "property"},
        "selectors": {
            "owner": ".owner-info .name",
            "assessed_value": ".assessed-value span",
            "tax_amount": ".tax-total span",
            "parcel": ".parcel-id",
            "address": ".property-address",
        },
        "permits_path": None,
    },
    "los_angeles_ca": {
        "label": "Los Angeles County, CA",
        "base_url": "https://portal.assessor.lacounty.gov",
        "search_path": "/parceldetail",
        "search_params": lambda addr: {"parcel": addr},
        "selectors": {
            "owner": "#ownerName",
            "assessed_value": "#assessedValue",
            "tax_amount": "#taxAmount",
            "parcel": "#parcelNumber",
            "address": "#propertyAddress",
        },
        "permits_path": None,
    },
}


def _resolve_county_key(county: str | None, state: str | None) -> str | None:
    """Return a config key like 'travis_tx' from user-supplied county/state."""
    if county is None or state is None:
        return None
    normalized = f"{county.strip().lower().replace(' ', '_')}_{state.strip().lower()}"
    if normalized in _COUNTY_CONFIGS:
        return normalized
    # Try matching just by county name prefix
    for key in _COUNTY_CONFIGS:
        if key.startswith(county.strip().lower().replace(" ", "_")):
            return key
    return None


class CountyRecordsConnector:
    """Property records from county assessor websites (scraping-based)."""

    name: str = "County Records"
    provider: str = "county_records"
    description: str = (
        "Look up property records from public county assessor databases. "
        "Returns owner, assessed value, tax amount, and parcel info."
    )

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; Agentary/1.0; "
                    "+https://github.com/agentary)"
                ),
            },
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _text(soup: BeautifulSoup, selector: str) -> str | None:
        tag = soup.select_one(selector)
        return tag.get_text(strip=True) if tag else None

    async def _scrape(
        self,
        config: dict[str, Any],
        address: str,
    ) -> list[dict[str, Any]]:
        url = config["base_url"] + config["search_path"]
        params = config["search_params"](address)

        response = await self._client.get(url, params=params)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        selectors = config["selectors"]

        record: dict[str, Any] = {
            "owner": self._text(soup, selectors["owner"]),
            "assessed_value": self._text(soup, selectors["assessed_value"]),
            "tax_amount": self._text(soup, selectors["tax_amount"]),
            "parcel": self._text(soup, selectors["parcel"]),
            "address": self._text(soup, selectors["address"]) or address,
            "county": config["label"],
        }

        # Only include record if at least one field was populated
        has_data = any(
            record.get(k) is not None
            for k in ("owner", "assessed_value", "tax_amount", "parcel")
        )
        return [record] if has_data else []

    # ------------------------------------------------------------------
    # core interface
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        address: str | None = None,
        county: str | None = None,
        state: str | None = None,
        **kwargs: Any,
    ) -> SourceResult:
        lookup_address = address or query
        county_key = _resolve_county_key(county, state)

        if county_key is None:
            supported = [cfg["label"] for cfg in _COUNTY_CONFIGS.values()]
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={
                    "county_supported": False,
                    "message": (
                        f"County not supported. "
                        f"Supported counties: {', '.join(supported)}"
                    ),
                },
            )

        config = _COUNTY_CONFIGS[county_key]
        try:
            records = await self._scrape(config, lookup_address)
        except Exception as exc:
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": str(exc),
                    "county": config["label"],
                    "message": "Scraping failed — site may have changed layout",
                },
            )

        return SourceResult(
            data=records,
            raw_response=None,
            total_results=len(records),
            source_name=self.name,
            source_url=config["base_url"],
            metadata={"county": config["label"]},
        )

    async def get(
        self,
        identifier: str,
        *,
        county: str | None = None,
        state: str | None = None,
        **kwargs: Any,
    ) -> SourceResult:
        return await self.search(
            identifier,
            address=identifier,
            county=county,
            state=state,
        )

    async def get_permits(
        self,
        address: str,
        county: str,
        state: str,
    ) -> SourceResult:
        """Return building permits for the given property (best-effort)."""
        county_key = _resolve_county_key(county, state)

        if county_key is None:
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={"county_supported": False, "message": "County not supported"},
            )

        config = _COUNTY_CONFIGS[county_key]
        if config.get("permits_path") is None:
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={
                    "county": config["label"],
                    "message": "Permit data not available for this county",
                },
            )

        # Placeholder for future per-county permit scraping
        return SourceResult(
            data=[],
            raw_response=None,
            total_results=0,
            source_name=self.name,
            metadata={"county": config["label"]},
        )

    async def health_check(self) -> dict[str, Any]:
        return {
            "status": "degraded",
            "latency_ms": 0,
            "message": (
                "Scraping-based connector — reliability depends on county "
                "website availability and layout stability"
            ),
        }

    def get_tool_definition(self) -> dict[str, Any]:
        return {
            "name": "county_records",
            "description": (
                "Look up property records from county assessor databases. "
                "Returns owner, assessed value, tax amount, parcel info."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Property address",
                    },
                    "county": {"type": "string"},
                    "state": {"type": "string"},
                },
                "required": ["address"],
            },
        }
