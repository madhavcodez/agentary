from __future__ import annotations

import httpx

from .base import Connector, RawOpportunity

LEVER_COMPANIES = [
    "netflix", "coinbase", "twitch", "reddit", "spotify",
    "dropbox", "lyft", "robinhood", "discord", "figma",
]


class LeverConnector(Connector):
    def __init__(self, companies: list[str] | None = None):
        self.companies = companies or LEVER_COMPANIES

    async def fetch(self) -> list[RawOpportunity]:
        results: list[RawOpportunity] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for company in self.companies:
                try:
                    resp = await client.get(f"https://api.lever.co/v0/postings/{company}")
                    if resp.status_code != 200:
                        continue
                    postings = resp.json()
                    for posting in postings:
                        location = posting.get("categories", {}).get("location", "")
                        results.append(RawOpportunity(
                            source="lever",
                            source_id=f"lv_{company}_{posting['id']}",
                            company=company.replace("-", " ").title(),
                            title=posting.get("text", ""),
                            location=location,
                            description=posting.get("descriptionPlain", ""),
                            url=posting.get("hostedUrl"),
                            raw_json=posting,
                        ))
                except Exception:
                    continue
        return results
