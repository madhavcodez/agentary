from __future__ import annotations

import httpx

from .. import gemini
from .base import Connector, RawOpportunity

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


class YCHNConnector(Connector):
    async def fetch(self) -> list[RawOpportunity]:
        results: list[RawOpportunity] = []
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    HN_SEARCH_URL,
                    params={
                        "query": "Ask HN: Who is hiring",
                        "tags": "story",
                        "numericFilters": "created_at_i>1740000000",
                    },
                )
                if resp.status_code != 200:
                    return results

                hits = resp.json().get("hits", [])
                if not hits:
                    return results

                story_id = hits[0]["objectID"]

                comments_resp = await client.get(
                    f"https://hn.algolia.com/api/v1/items/{story_id}"
                )
                if comments_resp.status_code != 200:
                    return results

                children = comments_resp.json().get("children", [])[:30]

                for child in children:
                    text = child.get("text", "")
                    if not text or len(text) < 50:
                        continue

                    try:
                        parsed = await gemini.generate_structured(
                            f"Parse this HN job posting into structured data:\n\n{text[:2000]}",
                            schema_hint='{"company":"string","title":"string","location":"string or null","description":"string"}',
                        )
                        results.append(RawOpportunity(
                            source="hn_whos_hiring",
                            source_id=f"hn_{child.get('id', '')}",
                            company=parsed.get("company", "Unknown"),
                            title=parsed.get("title", "Software Engineer"),
                            location=parsed.get("location"),
                            description=parsed.get("description", text[:1000]),
                            url=f"https://news.ycombinator.com/item?id={child.get('id', '')}",
                            raw_json={"text": text[:2000]},
                        ))
                    except Exception:
                        continue
            except Exception:
                pass
        return results
