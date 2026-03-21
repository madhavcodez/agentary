"""Base connector interface for all data source connectors.

Defines the SourceResult dataclass (normalized output) and the
SourceConnector protocol that every connector must implement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class SourceResult:
    """Normalized result returned by every data source connector."""

    data: list[dict[str, Any]]
    raw_response: Any
    total_results: int
    source_name: str
    source_url: str | None = None
    cost_usd: float = 0.0
    cached: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "data": self.data,
            "total_results": self.total_results,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "cost_usd": self.cost_usd,
            "cached": self.cached,
            "metadata": self.metadata,
        }


@runtime_checkable
class SourceConnector(Protocol):
    """Protocol that every data source connector must satisfy."""

    name: str
    provider: str
    description: str

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        """Search / query the source."""
        ...

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        """Get a specific record by ID or URL."""
        ...

    async def health_check(self) -> dict[str, Any]:
        """Return {status: healthy|degraded|down, latency_ms, message}."""
        ...

    def get_tool_definition(self) -> dict[str, Any]:
        """Return Gemini function-calling compatible tool definition."""
        ...
