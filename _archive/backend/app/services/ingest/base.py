from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class RawOpportunity:
    source: str
    source_id: str
    company: str
    title: str
    location: str | None
    description: str | None
    url: str | None
    raw_json: dict | None = None


class Connector(ABC):
    @abstractmethod
    async def fetch(self) -> list[RawOpportunity]:
        ...
