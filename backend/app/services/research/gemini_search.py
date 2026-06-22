"""Gemini with Google Search grounding for company research.

Uses the native Google Search tool built into Gemini to find real-time
company information without requiring an extra search API key.
"""

from __future__ import annotations

import contextlib
import json
import logging
from typing import Any

from google import genai
from google.genai import types

from ...config import settings

logger = logging.getLogger(__name__)

_RESEARCH_SCHEMA = """{
  "company_overview": "string — brief description of the company, what they do, industry",
  "recent_news": ["string — headline or summary of recent news item"],
  "funding": "string — latest funding round, amount raised, investors, or 'N/A'",
  "leadership": [{"name": "string", "title": "string"}],
  "culture": "string — engineering culture, values, work style",
  "hiring_activity": "string — current hiring trends, team growth signals",
  "company_size": "string — approximate employee count or range",
  "tech_stack": "string — known technologies used by engineering teams",
  "sources": ["string — URL of source used"]
}"""


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def gemini_research(company: str, role: str) -> dict[str, Any]:
    """Research a company using Gemini with Google Search grounding.

    Args:
        company: The company name to research.
        role: The job role being targeted (provides context).

    Returns:
        Structured dict with company intel fields.
    """
    client = _get_client()

    prompt = (
        f'Research "{company}" company for a "{role}" job application. '
        f"Find: company overview, recent news, funding, leadership team, "
        f"engineering culture, hiring activity, company size, and tech stack."
    )

    try:
        # Step 1: Search the web (plain text, can't use JSON mime with search tool)
        search_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.3,
            ),
        )
        raw_text = (search_response.text or "").strip()
        if not raw_text:
            logger.warning("Gemini search returned empty for %s", company)
            raw_text = f"Company: {company}. No search results available."

        # Step 2: Convert text research into structured JSON (no search tool)
        struct_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Convert this company research into structured JSON:\n\n{raw_text[:4000]}\n\nReturn ONLY valid JSON matching this schema:\n{_RESEARCH_SCHEMA}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        text = struct_response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        text = text.strip()

        result = json.loads(text)
        response = search_response  # for grounding metadata below

        # Ensure all expected keys exist with sensible defaults
        defaults: dict[str, Any] = {
            "company_overview": "",
            "recent_news": [],
            "funding": "Unknown",
            "leadership": [],
            "culture": "Unknown",
            "hiring_activity": "Unknown",
            "company_size": "Unknown",
            "tech_stack": "Unknown",
            "sources": [],
        }
        for key, default_val in defaults.items():
            if key not in result or result[key] is None:
                result[key] = default_val

        # Extract grounding sources from the response metadata if available
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            grounding_metadata = getattr(candidate, "grounding_metadata", None)
            if grounding_metadata:
                chunks = getattr(grounding_metadata, "grounding_chunks", None)
                if chunks:
                    for chunk in chunks:
                        web = getattr(chunk, "web", None)
                        if (
                            web
                            and hasattr(web, "uri")
                            and web.uri
                            and web.uri not in result["sources"]
                        ):
                            result["sources"].append(web.uri)

        return result

    except json.JSONDecodeError:
        logger.warning("Failed to parse Gemini research JSON for %s", company)
        # Attempt to extract JSON from response
        with contextlib.suppress(Exception):
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        return {
            "company_overview": f"Research for {company} returned non-JSON response.",
            "recent_news": [],
            "funding": "Unknown",
            "leadership": [],
            "culture": "Unknown",
            "hiring_activity": "Unknown",
            "company_size": "Unknown",
            "tech_stack": "Unknown",
            "sources": [],
        }
    except Exception as e:
        logger.error("Gemini research failed for %s: %s", company, e)
        return {
            "company_overview": f"Research unavailable: {e}",
            "recent_news": [],
            "funding": "Unknown",
            "leadership": [],
            "culture": "Unknown",
            "hiring_activity": "Unknown",
            "company_size": "Unknown",
            "tech_stack": "Unknown",
            "sources": [],
        }
