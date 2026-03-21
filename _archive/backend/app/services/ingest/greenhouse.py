from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from .base import Connector, RawOpportunity

BOARD_TOKENS = [
    "airbnb", "figma", "stripe", "notion", "anthropic",
    "databricks", "vercel", "linear", "openai", "scale",
    "anduril", "palantir", "meta", "google", "apple",
]


def _strip_html(html: str | None) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(separator="\n", strip=True)


class GreenhouseConnector(Connector):
    def __init__(self, board_tokens: list[str] | None = None):
        self.board_tokens = board_tokens or BOARD_TOKENS

    async def fetch(self) -> list[RawOpportunity]:
        results: list[RawOpportunity] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for token in self.board_tokens:
                try:
                    resp = await client.get(
                        f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                        params={"content": "true"},
                    )
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    for job in data.get("jobs", []):
                        location_name = ""
                        if job.get("location"):
                            location_name = job["location"].get("name", "")
                        results.append(RawOpportunity(
                            source="greenhouse",
                            source_id=f"gh_{token}_{job['id']}",
                            company=token.replace("-", " ").title(),
                            title=job.get("title", ""),
                            location=location_name,
                            description=_strip_html(job.get("content", "")),
                            url=job.get("absolute_url"),
                            raw_json=job,
                        ))
                except Exception:
                    continue
        return results
