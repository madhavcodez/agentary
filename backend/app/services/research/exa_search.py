"""Exa API integration for finding contacts at companies.

Uses the Exa search engine to discover recruiters, hiring managers,
and other relevant contacts at target companies via LinkedIn and
company career pages.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from exa_py import Exa

from ...config import settings
from ..circuit_breakers import exa_breaker

logger = logging.getLogger(__name__)


def _get_exa_client() -> Exa:
    return Exa(api_key=settings.exa_api_key)


def _extract_name_from_title(title: str | None) -> str:
    """Best-effort name extraction from a search result title.

    LinkedIn titles typically look like:
      "Jane Doe - Recruiter at Acme Corp | LinkedIn"
      "John Smith | Engineering Manager | LinkedIn"
    """
    if not title:
        return ""

    # Remove common suffixes
    cleaned = re.sub(r"\s*\|\s*LinkedIn.*$", "", title, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*-\s*LinkedIn.*$", "", cleaned, flags=re.IGNORECASE)

    # Take the first segment before a dash or pipe (likely the name)
    parts = re.split(r"\s*[-|]\s*", cleaned)
    name_candidate = parts[0].strip() if parts else cleaned.strip()

    # Basic validation: a name should be 2+ words, not too long
    words = name_candidate.split()
    if 1 <= len(words) <= 5 and len(name_candidate) < 80:
        return name_candidate

    return name_candidate[:80] if name_candidate else ""


def _extract_title_from_result(title: str | None) -> str:
    """Extract the professional title from a search result title string."""
    if not title:
        return ""

    cleaned = re.sub(r"\s*\|\s*LinkedIn.*$", "", title, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*-\s*LinkedIn.*$", "", cleaned, flags=re.IGNORECASE)

    parts = re.split(r"\s*[-|]\s*", cleaned)
    if len(parts) >= 2:
        # Second segment is typically the job title
        return parts[1].strip()

    return ""


def _extract_email(text: str) -> str | None:
    """Extract an email address from text."""
    if not text:
        return None
    match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> str | None:
    """Extract a phone number from text."""
    if not text:
        return None
    match = re.search(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text)
    return match.group(0) if match else None


def _deduplicate_contacts(contacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate contacts by URL and name."""
    seen_urls: set[str] = set()
    seen_names: set[str] = set()
    unique: list[dict[str, Any]] = []

    for c in contacts:
        url = c.get("url", "")
        name = c.get("name", "").lower().strip()

        # Skip if we already have this URL or this exact name
        if url and url in seen_urls:
            continue
        if name and name in seen_names:
            continue

        if url:
            seen_urls.add(url)
        if name:
            seen_names.add(name)
        unique.append(c)

    return unique


@exa_breaker
async def exa_find_contacts(company: str, role: str) -> list[dict[str, Any]]:
    """Search for recruiters and hiring managers at a company using Exa.

    Args:
        company: Company name to search contacts for.
        role: Target role title (provides search context).

    Returns:
        List of contact dicts with keys: name, title, company, url,
        source, snippet, email, phone.
    """
    if not settings.exa_api_key:
        logger.warning("Exa API key not configured; skipping contact search")
        return []

    exa = _get_exa_client()
    contacts: list[dict[str, Any]] = []

    queries = [
        f"{company} recruiter hiring {role} site:linkedin.com",
        f"{company} engineering manager site:linkedin.com",
        f"{company} talent acquisition site:linkedin.com",
        f"{company} careers contact email",
    ]

    for query in queries:
        try:
            results = exa.search(
                query,
                num_results=5,
                type="auto",
            )

            for r in results.results:
                snippet = r.text[:500] if r.text else ""
                email = _extract_email(snippet)
                phone = _extract_phone(snippet)

                contacts.append(
                    {
                        "name": _extract_name_from_title(r.title),
                        "title": _extract_title_from_result(r.title),
                        "company": company,
                        "url": r.url,
                        "source": "exa",
                        "snippet": snippet,
                        "email": email,
                        "phone": phone,
                    }
                )

        except Exception as e:
            logger.warning("Exa search failed for query '%s': %s", query, e)
            continue

    # Deduplicate and filter out entries without a name
    unique = _deduplicate_contacts(contacts)
    return [c for c in unique if c.get("name")]
