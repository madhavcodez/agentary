"""Web scraping tool for expert agents."""
from __future__ import annotations

from typing import Any

import httpx
from bs4 import BeautifulSoup

TOOL_SCHEMA: dict[str, Any] = {
    "name": "web_scraper",
    "description": "Fetch and extract text content from a web page URL. Returns cleaned text, title, and metadata.",
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to scrape",
            },
            "extract": {
                "type": "string",
                "description": "What to extract: text, tables, links, or all",
                "enum": ["text", "tables", "links", "all"],
                "default": "text",
            },
        },
        "required": ["url"],
    },
}


async def execute(url: str, extract: str = "text", **kwargs: Any) -> dict[str, Any]:
    """Fetch and parse a web page."""
    try:
        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Agentary/1.0)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove script, style, nav, footer
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        result: dict[str, Any] = {
            "tool": "web_scraper",
            "url": url,
            "title": soup.title.string.strip() if soup.title and soup.title.string else "",
            "status": "success",
        }

        if extract in ("text", "all"):
            text = soup.get_text(separator="\n", strip=True)
            # Collapse multiple newlines
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            result["text"] = "\n".join(lines)[:5000]

        if extract in ("tables", "all"):
            tables = []
            for table in soup.find_all("table")[:5]:
                rows = []
                for tr in table.find_all("tr"):
                    cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if cells:
                        rows.append(cells)
                if rows:
                    tables.append(rows)
            result["tables"] = tables

        if extract in ("links", "all"):
            links = []
            for a in soup.find_all("a", href=True)[:50]:
                href = a["href"]
                if href.startswith("http"):
                    links.append({"text": a.get_text(strip=True), "url": href})
            result["links"] = links

        return result
    except Exception as e:
        return {
            "tool": "web_scraper",
            "url": url,
            "error": str(e),
            "status": "error",
        }
