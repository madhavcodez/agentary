"""Central registry for all data source connectors."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .base_connector import SourceConnector, SourceResult

logger = logging.getLogger(__name__)


class SourceRegistry:
    def __init__(self):
        self._connectors: dict[str, SourceConnector] = {}

    def register(self, connector: SourceConnector):
        self._connectors[connector.provider] = connector
        logger.info("Registered data source connector: %s", connector.provider)

    def get(self, provider: str) -> SourceConnector | None:
        return self._connectors.get(provider)

    def list_available(self) -> list[dict[str, Any]]:
        return [
            {
                "provider": c.provider,
                "name": c.name,
                "description": c.description,
            }
            for c in self._connectors.values()
        ]

    def get_tool_definitions(
        self, providers: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        targets = providers or list(self._connectors.keys())
        return [
            self._connectors[p].get_tool_definition()
            for p in targets
            if p in self._connectors
        ]

    async def query(
        self, provider: str, method: str = "search", **kwargs: Any,
    ) -> SourceResult:
        connector = self.get(provider)
        if not connector:
            raise ValueError(f"Unknown provider: {provider}")
        fn = getattr(connector, method)
        return await fn(**kwargs)

    async def health_check_all(self) -> dict[str, dict]:
        results = {}
        tasks = []
        providers = []
        for provider, connector in self._connectors.items():
            providers.append(provider)
            tasks.append(connector.health_check())
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        for provider, outcome in zip(providers, outcomes):
            if isinstance(outcome, Exception):
                results[provider] = {"status": "down", "message": str(outcome)}
            else:
                results[provider] = outcome
        return results


def create_source_registry(settings) -> SourceRegistry:
    """Factory function called on app startup. Import connectors lazily."""
    from .connectors.county_records import CountyRecordsConnector
    from .connectors.crunchbase import CrunchbaseConnector
    from .connectors.custom_api import CustomAPIConnector
    from .connectors.exa import ExaConnector
    from .connectors.gemini_search import GeminiSearchConnector
    from .connectors.google_places import GooglePlacesConnector
    from .connectors.python_executor import PythonExecutorConnector
    from .connectors.web_scraper import WebScraperConnector
    from .connectors.yelp import YelpConnector
    from .connectors.zillow import ZillowConnector

    registry = SourceRegistry()

    # Always available (no API key needed)
    registry.register(
        WebScraperConnector(
            gemini_api_key=getattr(settings, "gemini_api_key", ""),
        ),
    )
    registry.register(PythonExecutorConnector())

    # Require API keys -- skip with warning if missing
    if getattr(settings, "gemini_api_key", None):
        registry.register(GeminiSearchConnector(settings.gemini_api_key))
    else:
        logger.warning("GEMINI_API_KEY not set -- GeminiSearchConnector disabled")

    if getattr(settings, "exa_api_key", None):
        registry.register(ExaConnector(settings.exa_api_key))
    else:
        logger.warning("EXA_API_KEY not set -- ExaConnector disabled")

    if getattr(settings, "google_places_api_key", None):
        registry.register(GooglePlacesConnector(settings.google_places_api_key))
    else:
        logger.warning(
            "GOOGLE_PLACES_API_KEY not set -- GooglePlacesConnector disabled",
        )

    if getattr(settings, "zillow_api_key", None):
        registry.register(ZillowConnector(settings.zillow_api_key))
    else:
        logger.warning("ZILLOW_API_KEY not set -- ZillowConnector disabled")

    if getattr(settings, "yelp_api_key", None):
        registry.register(YelpConnector(settings.yelp_api_key))
    else:
        logger.warning("YELP_API_KEY not set -- YelpConnector disabled")

    if getattr(settings, "crunchbase_api_key", None):
        registry.register(CrunchbaseConnector(settings.crunchbase_api_key))
    else:
        logger.warning(
            "CRUNCHBASE_API_KEY not set -- CrunchbaseConnector disabled",
        )

    return registry
