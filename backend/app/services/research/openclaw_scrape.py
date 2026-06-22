"""Web scraping via the OpenClaw browser automation container.

Falls back to plain httpx GET requests when the OpenClaw API
is unavailable or returns errors. Designed to extract career page
info and public profile data.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from ...config import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0


async def openclaw_scrape(url: str) -> str:
    """Scrape a web page and return its text content.

    Tries the OpenClaw container first (POST /api/scrape). If that
    fails, falls back to a direct httpx GET with HTML tag stripping.

    Args:
        url: The URL to scrape.

    Returns:
        Extracted text content (may be empty on failure).
    """
    # Try OpenClaw container first
    text = await _try_openclaw(url)
    if text:
        return text

    # Fallback: direct HTTP fetch + basic HTML strip
    return await _direct_fetch(url)


async def _try_openclaw(url: str) -> str:
    """Attempt to scrape via the OpenClaw API."""
    openclaw_base = settings.openclaw_url
    if not openclaw_base:
        return ""

    # Try several known OpenClaw endpoint patterns
    endpoints = [
        f"{openclaw_base}/api/scrape",
        f"{openclaw_base}/api/browse",
        f"{openclaw_base}/scrape",
    ]

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for endpoint in endpoints:
            try:
                resp = await client.post(
                    endpoint,
                    json={"url": url, "extract_text": True},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    # Handle various response shapes
                    if isinstance(data, dict):
                        return (
                            data.get("text", "") or data.get("content", "") or data.get("body", "")
                        )
                    if isinstance(data, str):
                        return data
            except httpx.ConnectError:
                logger.debug("OpenClaw not reachable at %s", endpoint)
            except Exception as e:
                logger.debug("OpenClaw endpoint %s failed: %s", endpoint, e)

    return ""


async def _direct_fetch(url: str) -> str:
    """Fetch a page directly and strip HTML tags."""
    try:
        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return ""
            return _strip_html(resp.text)
    except Exception as e:
        logger.debug("Direct fetch failed for %s: %s", url, e)
        return ""


def _strip_html(html: str) -> str:
    """Crude HTML to text conversion."""
    # Remove script and style blocks
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:10_000]  # Cap to avoid huge payloads


def _normalize_company(company: str) -> str:
    """Normalize a company name for URL construction."""
    return re.sub(r"[^a-z0-9]", "", company.lower())


async def scrape_company_careers(company: str) -> dict[str, Any]:
    """Scrape a company's careers page for contact info and job details.

    Tries common career page URL patterns and extracts emails,
    phone numbers, and hiring team references.

    Args:
        company: Company name.

    Returns:
        Dict with keys: career_page_text, emails, phones, urls_tried.
    """
    slug = _normalize_company(company)
    urls = [
        f"https://www.{slug}.com/careers",
        f"https://careers.{slug}.com",
        f"https://www.{slug}.com/jobs",
        f"https://{slug}.com/careers",
    ]

    result: dict[str, Any] = {
        "career_page_text": "",
        "emails": [],
        "phones": [],
        "urls_tried": urls,
    }

    for url in urls:
        text = await openclaw_scrape(url)
        if text and len(text) > 100:
            result["career_page_text"] = text[:5_000]
            # Extract emails
            emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
            result["emails"] = list(set(emails))
            # Extract phone numbers
            phones = re.findall(
                r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
                text,
            )
            result["phones"] = list(set(phones))
            break

    return result


async def scrape_linkedin_profile(linkedin_url: str) -> dict[str, Any]:
    """Best-effort scrape of a public LinkedIn profile.

    LinkedIn aggressively blocks scrapers, so this returns whatever
    public info is available (typically very limited).

    Args:
        linkedin_url: Full LinkedIn profile URL.

    Returns:
        Dict with keys: name, headline, text.
    """
    text = await openclaw_scrape(linkedin_url)

    result: dict[str, Any] = {
        "name": "",
        "headline": "",
        "text": text[:3_000] if text else "",
    }

    if text:
        # Attempt naive extraction from page text
        # LinkedIn public profiles sometimes have "Name - Title | LinkedIn"
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if lines:
            result["name"] = lines[0][:100]
        if len(lines) > 1:
            result["headline"] = lines[1][:200]

    return result
