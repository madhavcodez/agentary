"""Exa API integration for finding contacts at companies.

Discovers recruiters, hiring managers, and other relevant contacts at
target companies via LinkedIn and company career pages. All Exa SDK
access goes through the shared ``ExaProvider`` adapter — this module
just composes domain-specific queries.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from ...platform.infrastructure.providers import exa_provider
from ...platform.infrastructure.providers.exa import ExaUnavailable

logger = logging.getLogger(__name__)


def _extract_name_from_title(title: str | None) -> str:
    """Best-effort name extraction from a search result title.

    LinkedIn titles typically look like:
      "Jane Doe - Recruiter at Acme Corp | LinkedIn"
      "John Smith | Engineering Manager | LinkedIn"
    """
    if not title:
        return ""

    cleaned = re.sub(r"\s*\|\s*LinkedIn.*$", "", title, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*-\s*LinkedIn.*$", "", cleaned, flags=re.IGNORECASE)

    parts = re.split(r"\s*[-|]\s*", cleaned)
    name_candidate = parts[0].strip() if parts else cleaned.strip()

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
        return parts[1].strip()

    return ""


def _extract_email(text: str) -> str | None:
    if not text:
        return None
    match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> str | None:
    if not text:
        return None
    match = re.search(
        r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", text
    )
    return match.group(0) if match else None


def _deduplicate_contacts(contacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen_urls: set[str] = set()
    seen_names: set[str] = set()
    unique: list[dict[str, Any]] = []

    for c in contacts:
        url = c.get("url", "")
        name = c.get("name", "").lower().strip()

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


async def exa_find_contacts(
    company: str, role: str
) -> list[dict[str, Any]]:
    """Search for recruiters and hiring managers at a company using Exa.

    The circuit breaker for Exa lives on the provider itself, so this
    function no longer needs the ``@exa_breaker`` decorator.
    """
    if not exa_provider.is_configured:
        logger.warning("Exa API key not configured; skipping contact search")
        return []

    contacts: list[dict[str, Any]] = []
    queries = [
        f"{company} recruiter hiring {role} site:linkedin.com",
        f"{company} engineering manager site:linkedin.com",
        f"{company} talent acquisition site:linkedin.com",
        f"{company} careers contact email",
    ]

    for query in queries:
        try:
            results = await exa_provider.search(
                query,
                num_results=5,
                search_type="auto",
                include_text=True,
                max_text_chars=500,
            )
        except ExaUnavailable as exc:
            logger.warning("Exa unavailable for '%s': %s", query, exc)
            continue
        except Exception as exc:
            logger.warning("Exa search failed for '%s': %s", query, exc)
            continue

        for r in results:
            snippet = r.snippet
            contacts.append(
                {
                    "name": _extract_name_from_title(r.title),
                    "title": _extract_title_from_result(r.title),
                    "company": company,
                    "url": r.url,
                    "source": "exa",
                    "snippet": snippet,
                    "email": _extract_email(snippet),
                    "phone": _extract_phone(snippet),
                }
            )

    unique = _deduplicate_contacts(contacts)
    return [c for c in unique if c.get("name")]
