"""Post-processing for completed calls.

Classifies call outcome, generates a summary, and extracts
structured data from the transcript using Gemini.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from .gemini import generate_structured

logger = logging.getLogger(__name__)

_ANALYSIS_PROMPT_TEMPLATE = """\
Analyze this phone call transcript and extract the following information.

## Transcript
{transcript}

## Required Output
Return a JSON object with these fields:
1. call_outcome: one of ("successful", "partial", "unsuccessful", "voicemail", "no_answer")
2. summary: 2-3 sentence summary of the call
3. key_data_points: list of objects with {{name, value, confidence}} — extracted data from the call
4. sentiment: one of ("positive", "neutral", "negative")
5. call_quality_score: a float from 0.0 to 1.0 indicating overall call quality
"""

_SCHEMA_HINT = """\
{
  "call_outcome": "string",
  "summary": "string",
  "key_data_points": [{"name": "string", "value": "string", "confidence": 0.9}],
  "sentiment": "string",
  "call_quality_score": 0.85
}
"""


async def process_call_result(
    db: Session,
    call_log: Any,
    transcript_text: str,
) -> None:
    """Analyze a completed call transcript and update the call log.

    Steps:
    1. Classify the call outcome using Gemini.
    2. Generate a summary of the conversation.
    3. Extract structured data points.
    4. Update the CallRecord/CallLog with results.

    Args:
        db: Active database session.
        call_log: The CallLog or CallRecord to update.
        transcript_text: Full transcript of the call.
    """
    if not transcript_text or not transcript_text.strip():
        logger.info("Empty transcript — skipping post-processing")
        return

    logger.info(
        "Post-processing call_log=%s transcript_len=%d",
        call_log.id,
        len(transcript_text),
    )

    # Truncate very long transcripts to stay within model limits
    truncated = transcript_text[:15_000]

    try:
        analysis = await generate_structured(
            prompt=_ANALYSIS_PROMPT_TEMPLATE.format(transcript=truncated),
            schema_hint=_SCHEMA_HINT,
        )

        # Update outcome
        outcome = analysis.get("call_outcome", "")
        if outcome:
            call_log.outcome = outcome

        # Update summary (store in transcript notes or a dedicated field)
        summary = analysis.get("summary", "")
        if summary and hasattr(call_log, "extraction_notes"):
            call_log.extraction_notes = summary

        # Update extracted_data
        key_data_points = analysis.get("key_data_points", [])
        if hasattr(call_log, "extracted_data") and key_data_points:
            call_log.extracted_data = {
                "key_data_points": key_data_points,
                "summary": summary,
                "call_outcome": outcome,
            }

        # Update sentiment
        sentiment = analysis.get("sentiment", "")
        if hasattr(call_log, "sentiment") and sentiment:
            call_log.sentiment = sentiment

        # Update call quality score
        quality_score = analysis.get("call_quality_score")
        if hasattr(call_log, "call_quality_score") and quality_score is not None:
            try:
                call_log.call_quality_score = max(0.0, min(1.0, float(quality_score)))
            except (TypeError, ValueError):
                logger.warning("Invalid call_quality_score from Gemini: %s", quality_score)

        db.commit()
        logger.info(
            "Post-processing complete for call_log=%s outcome=%s sentiment=%s score=%s",
            call_log.id, outcome, sentiment, quality_score,
        )

    except Exception as exc:
        # Log and continue — don't fail the whole extraction pipeline
        logger.error(
            "Gemini post-processing failed for call_log=%s: %s",
            call_log.id, exc,
            exc_info=True,
        )
        if hasattr(call_log, "extraction_notes"):
            call_log.extraction_notes = f"post-processing failed: {exc}"
            db.commit()
