"""Web scraper connector — fetch and extract structured data from web pages.

Supports multiple extraction modes: plain text, HTML tables, CSS selectors,
and AI-powered extraction via Gemini. Respects robots.txt and handles
common HTTP errors gracefully.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from ....config import settings
from ..base_connector import SourceResult

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0
_MAX_TEXT_LENGTH = 10_000
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _default_headers() -> dict[str, str]:
    return {
        "User-Agent": _USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


async def _check_robots_txt(url: str, client: httpx.AsyncClient) -> bool:
    """Check whether robots.txt allows scraping this URL.

    Returns True if scraping is allowed (or robots.txt is unavailable).
    """
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        resp = await client.get(robots_url, timeout=5.0)
        if resp.status_code != 200:
            return True  # No robots.txt found — allow

        path = parsed.path or "/"
        robots_text = resp.text.lower()

        # Simple robots.txt parsing: look for Disallow rules in User-agent: *
        in_wildcard_section = False
        for line in robots_text.splitlines():
            line = line.strip()
            if line.startswith("user-agent:"):
                agent = line.split(":", 1)[1].strip()
                in_wildcard_section = agent == "*"
            elif in_wildcard_section and line.startswith("disallow:"):
                disallowed = line.split(":", 1)[1].strip()
                if disallowed and path.lower().startswith(disallowed):
                    logger.info(
                        "robots.txt disallows scraping %s (rule: %s)",
                        url,
                        disallowed,
                    )
                    return False
        return True

    except Exception:
        return True  # If robots.txt check fails, allow


def _clean_text(soup: BeautifulSoup) -> str:
    """Extract clean text from a parsed HTML document."""
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:_MAX_TEXT_LENGTH]


def _extract_tables(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract HTML tables as lists of row dicts."""
    tables: list[dict[str, Any]] = []
    for table_el in soup.find_all("table"):
        rows = table_el.find_all("tr")
        if not rows:
            continue

        # Try to find headers
        header_row = rows[0]
        headers = [
            th.get_text(strip=True) for th in header_row.find_all(["th", "td"])
        ]
        if not headers:
            continue

        table_data: list[dict[str, str]] = []
        for row in rows[1:]:
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cells) == len(headers):
                table_data.append(dict(zip(headers, cells)))
            elif cells:
                # Pad or truncate to match headers
                padded = cells + [""] * (len(headers) - len(cells))
                table_data.append(dict(zip(headers, padded[:len(headers)])))

        tables.append({
            "headers": headers,
            "rows": table_data,
            "row_count": len(table_data),
        })

    return tables


def _extract_by_selectors(
    soup: BeautifulSoup, selectors: list[dict[str, str]]
) -> dict[str, Any]:
    """Extract data using CSS selectors.

    Each selector dict should have ``name`` (field name) and
    ``description`` (CSS selector string).
    """
    extracted: dict[str, Any] = {}
    for sel in selectors:
        name = sel.get("name", "")
        css = sel.get("description", "")
        if not name or not css:
            continue
        elements = soup.select(css)
        if len(elements) == 1:
            extracted[name] = elements[0].get_text(strip=True)
        elif elements:
            extracted[name] = [el.get_text(strip=True) for el in elements]
        else:
            extracted[name] = None
    return extracted


async def _ai_extract(
    text: str, fields: list[dict[str, str]]
) -> dict[str, Any]:
    """Use Gemini to extract structured fields from page text."""
    if not settings.gemini_api_key:
        logger.warning("Gemini API key not available for AI extraction")
        return {"error": "Gemini API key not configured for AI extraction"}

    from google import genai
    from google.genai import types

    field_descriptions = "\n".join(
        f'- "{f["name"]}": {f.get("description", "extract this field")}'
        for f in fields
    )

    prompt = (
        f"Extract the following fields from this web page text.\n"
        f"Return ONLY valid JSON with these fields:\n"
        f"{field_descriptions}\n\n"
        f"Web page text:\n{text[:8000]}\n\n"
        f"Return ONLY the JSON object, no markdown formatting."
    )

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        result_text = (response.text or "").strip()
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[-1]
        if result_text.endswith("```"):
            result_text = result_text.rsplit("```", 1)[0]
        result_text = result_text.strip()

        return json.loads(result_text)

    except json.JSONDecodeError:
        logger.warning("AI extraction returned non-JSON response")
        return {"raw_response": result_text[:2000]}
    except Exception as e:
        logger.error("AI extraction failed: %s", e)
        return {"error": str(e)}


class WebScraperConnector:
    """Data source connector for general web scraping and extraction."""

    name: str = "web_scraper"
    provider: str = "web"
    description: str = (
        "Fetch and extract structured data from any web page. "
        "Supports text, table, CSS selector, and AI-powered extraction."
    )

    async def _fetch_page(self, url: str) -> tuple[str, int]:
        """Fetch a web page and return (html_content, status_code).

        Returns ("", status_code) on failure.
        """
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers=_default_headers(),
        ) as client:
            # Respect robots.txt
            allowed = await _check_robots_txt(url, client)
            if not allowed:
                logger.warning("Blocked by robots.txt: %s", url)
                return "", 403

            resp = await client.get(url)
            return resp.text, resp.status_code

    async def get(self, identifier: str, **kwargs: Any) -> SourceResult:
        """Fetch a web page and extract data.

        Args:
            identifier: URL to scrape.
            **kwargs: Optional ``extract_type`` (str, default "auto"),
                      ``extract_fields`` (list of dicts with name/description).

        Returns:
            SourceResult with extracted data.
        """
        url = identifier
        extract_type = kwargs.get("extract_type", "auto")
        extract_fields = kwargs.get("extract_fields")

        try:
            html, status_code = await self._fetch_page(url)

            if status_code == 403:
                return SourceResult(
                    data=[],
                    raw_response=None,
                    total_results=0,
                    source_name=self.name,
                    source_url=url,
                    metadata={
                        "error": "Blocked by robots.txt or access denied",
                        "status_code": 403,
                    },
                )

            if status_code == 429:
                return SourceResult(
                    data=[],
                    raw_response=None,
                    total_results=0,
                    source_name=self.name,
                    source_url=url,
                    metadata={
                        "error": "Rate limited (429)",
                        "status_code": 429,
                    },
                )

            if status_code != 200:
                return SourceResult(
                    data=[],
                    raw_response=None,
                    total_results=0,
                    source_name=self.name,
                    source_url=url,
                    metadata={
                        "error": f"HTTP {status_code}",
                        "status_code": status_code,
                    },
                )

            if not html:
                return SourceResult(
                    data=[],
                    raw_response=None,
                    total_results=0,
                    source_name=self.name,
                    source_url=url,
                    metadata={"error": "Empty response body"},
                )

            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.get_text(strip=True) if soup.title else ""

            # Route to the appropriate extraction method
            if extract_type == "text":
                extracted = await self._extract_text(soup, url, title)
            elif extract_type == "tables":
                extracted = await self._extract_tables_mode(soup, url, title)
            elif extract_type == "selectors":
                extracted = await self._extract_selectors_mode(
                    soup, url, title, extract_fields or []
                )
            elif extract_type == "ai_extract":
                extracted = await self._extract_ai_mode(
                    soup, url, title, extract_fields or []
                )
            elif extract_type == "auto":
                extracted = await self._extract_auto(
                    soup, url, title, extract_fields
                )
            else:
                extracted = await self._extract_text(soup, url, title)

            return extracted

        except httpx.TimeoutException:
            logger.error("Timeout scraping %s", url)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                source_url=url,
                metadata={"error": "Request timed out"},
            )
        except httpx.ConnectError as e:
            logger.error("Connection error for %s: %s", url, e)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                source_url=url,
                metadata={"error": f"Connection failed: {e}"},
            )
        except Exception as e:
            logger.error("Scraping failed for %s: %s", url, e)
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                source_url=url,
                metadata={"error": str(e)},
            )

    async def _extract_text(
        self, soup: BeautifulSoup, url: str, title: str
    ) -> SourceResult:
        """Extract all text content from the page."""
        text = _clean_text(soup)
        return SourceResult(
            data=[{
                "url": url,
                "title": title,
                "text": text,
                "extract_type": "text",
                "source": "web_scraper",
            }],
            raw_response=text,
            total_results=1,
            source_name=self.name,
            source_url=url,
        )

    async def _extract_tables_mode(
        self, soup: BeautifulSoup, url: str, title: str
    ) -> SourceResult:
        """Extract HTML tables from the page."""
        tables = _extract_tables(soup)
        return SourceResult(
            data=[{
                "url": url,
                "title": title,
                "tables": tables,
                "table_count": len(tables),
                "extract_type": "tables",
                "source": "web_scraper",
            }],
            raw_response=tables,
            total_results=len(tables),
            source_name=self.name,
            source_url=url,
        )

    async def _extract_selectors_mode(
        self,
        soup: BeautifulSoup,
        url: str,
        title: str,
        selectors: list[dict[str, str]],
    ) -> SourceResult:
        """Extract data using CSS selectors."""
        extracted = _extract_by_selectors(soup, selectors)
        return SourceResult(
            data=[{
                "url": url,
                "title": title,
                "extracted": extracted,
                "extract_type": "selectors",
                "source": "web_scraper",
            }],
            raw_response=extracted,
            total_results=1,
            source_name=self.name,
            source_url=url,
        )

    async def _extract_ai_mode(
        self,
        soup: BeautifulSoup,
        url: str,
        title: str,
        fields: list[dict[str, str]],
    ) -> SourceResult:
        """Send page text to Gemini for structured extraction."""
        text = _clean_text(soup)
        ai_result = await _ai_extract(text, fields)
        return SourceResult(
            data=[{
                "url": url,
                "title": title,
                "extracted": ai_result,
                "extract_type": "ai_extract",
                "source": "web_scraper",
            }],
            raw_response=ai_result,
            total_results=1,
            source_name=self.name,
            source_url=url,
        )

    async def _extract_auto(
        self,
        soup: BeautifulSoup,
        url: str,
        title: str,
        extract_fields: list[dict[str, str]] | None,
    ) -> SourceResult:
        """Auto-determine extraction mode.

        If extract_fields are provided, uses AI extraction.
        If Gemini is available, uses AI to determine what is interesting.
        Otherwise, falls back to text extraction.
        """
        if extract_fields:
            return await self._extract_ai_mode(soup, url, title, extract_fields)

        text = _clean_text(soup)

        # If Gemini is available, use it for smart extraction
        if settings.gemini_api_key:
            auto_fields = [
                {"name": "summary", "description": "Brief summary of the page content"},
                {"name": "main_topics", "description": "Key topics or subjects covered"},
                {"name": "key_facts", "description": "Important facts, numbers, or data points"},
                {"name": "contact_info", "description": "Any contact information found"},
            ]
            ai_result = await _ai_extract(text, auto_fields)
            return SourceResult(
                data=[{
                    "url": url,
                    "title": title,
                    "text": text[:2000],
                    "ai_extracted": ai_result,
                    "extract_type": "auto",
                    "source": "web_scraper",
                }],
                raw_response=ai_result,
                total_results=1,
                source_name=self.name,
                source_url=url,
            )

        # Fallback: plain text extraction
        return await self._extract_text(soup, url, title)

    async def search(self, query: str, **kwargs: Any) -> SourceResult:
        """Search within provided URLs or return an error.

        Args:
            query: Text to search for within pages.
            **kwargs: Optional ``urls`` (list of str) to scrape and search.

        Returns:
            SourceResult with matching snippets.
        """
        urls = kwargs.get("urls")
        if not urls:
            return SourceResult(
                data=[],
                raw_response=None,
                total_results=0,
                source_name=self.name,
                metadata={
                    "error": (
                        "web_scraper.search() requires 'urls' parameter. "
                        "Use get() for single-URL scraping."
                    )
                },
            )

        results: list[dict[str, Any]] = []
        query_lower = query.lower()

        for url in urls:
            try:
                page_result = await self.get(url, extract_type="text")
                if page_result.data:
                    page_text = page_result.data[0].get("text", "")
                    if query_lower in page_text.lower():
                        # Find context around matches
                        idx = page_text.lower().find(query_lower)
                        start = max(0, idx - 200)
                        end = min(len(page_text), idx + len(query) + 200)
                        snippet = page_text[start:end]

                        results.append({
                            "url": url,
                            "title": page_result.data[0].get("title", ""),
                            "snippet": snippet,
                            "match_position": idx,
                            "source": "web_scraper",
                        })
            except Exception as e:
                logger.warning("Failed to search URL %s: %s", url, e)
                continue

        return SourceResult(
            data=results,
            raw_response=None,
            total_results=len(results),
            source_name=self.name,
            metadata={"query": query, "urls_searched": len(urls)},
        )

    async def health_check(self) -> dict[str, Any]:
        """Verify web scraping capability with a test request.

        Returns:
            Dict with ``status``, ``latency_ms``, and ``message``.
        """
        start = time.time()
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                headers=_default_headers(),
            ) as client:
                resp = await client.get("https://httpbin.org/get")
                resp.raise_for_status()
            latency = round((time.time() - start) * 1000, 1)
            return {
                "status": "healthy",
                "latency_ms": latency,
                "message": "Web scraper operational",
            }
        except Exception as e:
            latency = round((time.time() - start) * 1000, 1)
            return {
                "status": "down",
                "latency_ms": latency,
                "message": f"Web scraper error: {e}",
            }

    def get_tool_definition(self) -> dict[str, Any]:
        """Return Gemini function-calling compatible tool definition."""
        return {
            "name": "web_scraper",
            "description": (
                "Fetch and extract structured data from any web page. "
                "Supports text, table, CSS selector, and AI-powered extraction."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to scrape",
                    },
                    "extract_type": {
                        "type": "string",
                        "enum": [
                            "auto",
                            "text",
                            "tables",
                            "selectors",
                            "ai_extract",
                        ],
                        "default": "auto",
                    },
                    "extract_fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                            },
                        },
                        "description": (
                            "Fields to extract (for ai_extract mode)"
                        ),
                    },
                },
                "required": ["url"],
            },
        }
