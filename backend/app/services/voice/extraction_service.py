"""Extract structured data from call transcripts using AI."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from ...models.finding import Finding, FindingType, SourceType
from ...models.voice_extraction import CallRecord, VoiceExtraction
from ..gemini import generate_structured

logger = logging.getLogger(__name__)

# Minimum confidence threshold for creating a Finding from an extracted field.
_MIN_FINDING_CONFIDENCE = 0.4

# Supported field types and their basic validators.
_FIELD_TYPE_VALIDATORS: dict[str, type | tuple[type, ...]] = {
    "string": (str,),
    "text": (str,),
    "number": (int, float),
    "integer": (int,),
    "float": (float, int),
    "boolean": (bool,),
    "date": (str,),
    "email": (str,),
    "phone": (str,),
    "url": (str,),
    "currency": (int, float, str),
    "percentage": (int, float),
    "list": (list,),
    "enum": (str,),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def extract_from_transcript(
    call_record: CallRecord,
    voice_extraction: VoiceExtraction,
    db: Session,
) -> dict[str, Any]:
    """Extract structured data from a call record's transcript.

    Uses the extraction_schema from the parent VoiceExtraction to know which
    fields to extract from the CallRecord's transcript.

    Args:
        call_record: CallRecord with transcript populated.
        voice_extraction: Parent VoiceExtraction with extraction_schema.
        db: Database session.

    Returns:
        Dict with:
        - fields: [{field_name, value, confidence, transcript_reference}]
        - overall_confidence: float
        - quality_score: float (0-1)
    """
    transcript = call_record.transcript or ""
    schema = voice_extraction.extraction_schema or {}
    goals: list[dict[str, Any]] = schema.get("fields", [])

    if not transcript.strip():
        logger.warning(
            "extract_from_transcript called with empty transcript for "
            "call_record %s",
            call_record.id,
        )
        return {"fields": [], "overall_confidence": 0.0, "quality_score": 0.0}

    if not goals:
        logger.warning(
            "extract_from_transcript called with no extraction fields for "
            "voice_extraction %s",
            voice_extraction.id,
        )
        return {"fields": [], "overall_confidence": 0.0, "quality_score": 0.0}

    prompt = _build_extraction_prompt(transcript, goals)
    schema_hint = _build_schema_hint(goals)

    try:
        raw_result = await generate_structured(prompt, schema_hint=schema_hint)
    except Exception:
        logger.exception(
            "Gemini extraction failed for call_record %s", call_record.id
        )
        return {"fields": [], "overall_confidence": 0.0, "quality_score": 0.0}

    raw_fields: list[dict[str, Any]] = raw_result.get("fields", [])

    validated_fields: list[dict[str, Any]] = []
    for raw_field in raw_fields:
        field_name = raw_field.get("field_name", "")
        value = raw_field.get("value")
        confidence = _clamp(float(raw_field.get("confidence", 0.0)), 0.0, 1.0)
        transcript_ref = raw_field.get("transcript_reference", "")

        goal_spec = _find_goal_spec(field_name, goals)

        if goal_spec is not None and value is not None:
            if not _validate_extraction(goal_spec, value):
                logger.info(
                    "Extracted value for '%s' failed validation; "
                    "discarding (value=%r)",
                    field_name,
                    value,
                )
                confidence = min(confidence, 0.2)
                value = None

        validated_fields.append(
            {
                "field_name": field_name,
                "value": value,
                "confidence": confidence,
                "transcript_reference": transcript_ref,
            }
        )

    overall_confidence = _compute_overall_confidence(validated_fields)
    quality_score = _compute_quality_score(validated_fields, goals)

    result: dict[str, Any] = {
        "fields": validated_fields,
        "overall_confidence": overall_confidence,
        "quality_score": quality_score,
    }

    # Persist summary back onto the call record.
    call_record.extracted_data = {
        f["field_name"]: f["value"]
        for f in validated_fields
        if f["value"] is not None
    }
    call_record.extraction_confidence = overall_confidence
    db.add(call_record)
    db.flush()

    logger.info(
        "Extraction complete for call_record %s: %d fields, "
        "confidence=%.2f, quality=%.2f",
        call_record.id,
        len(validated_fields),
        overall_confidence,
        quality_score,
    )

    return result


async def extract_findings(
    call_record: CallRecord,
    voice_extraction: VoiceExtraction,
    extraction_result: dict[str, Any],
    db: Session,
) -> list[Finding]:
    """Convert extraction results into Finding objects and persist them.

    Creates one Finding per extracted field that has sufficient confidence.

    Args:
        call_record: CallRecord the findings originate from.
        voice_extraction: Parent VoiceExtraction.
        extraction_result: Output from extract_from_transcript().
        db: Database session.

    Returns:
        List of created Finding objects.
    """
    fields: list[dict[str, Any]] = extraction_result.get("fields", [])
    created: list[Finding] = []

    for field in fields:
        confidence: float = field.get("confidence", 0.0)
        value = field.get("value")

        if value is None or confidence < _MIN_FINDING_CONFIDENCE:
            continue

        field_name: str = field.get("field_name", "unknown")
        transcript_ref: str = field.get("transcript_reference", "")

        content_parts = [f"{field_name}: {value}"]
        if transcript_ref:
            content_parts.append(f'\nSource quote: "{transcript_ref}"')

        finding = Finding(
            id=uuid.uuid4(),
            project_id=voice_extraction.project_id,
            mission_id=voice_extraction.mission_id,
            call_record_id=call_record.id,
            finding_type=_finding_type_for_field(field_name),
            title=f"{field_name} (voice extraction)",
            content="\n".join(content_parts),
            structured_data={
                "field_name": field_name,
                "value": value,
                "transcript_reference": transcript_ref,
            },
            source_type=SourceType.voice_call,
            source_name=call_record.target_name or "voice call",
            confidence=confidence,
        )
        db.add(finding)
        created.append(finding)

    if created:
        db.flush()
        logger.info(
            "Created %d findings for call_record %s", len(created), call_record.id
        )

    return created


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_extraction_prompt(transcript: str, goals: list[dict]) -> str:
    """Build the Gemini prompt for data extraction."""
    goal_descriptions: list[str] = []
    for idx, goal in enumerate(goals, 1):
        name = goal.get("name", goal.get("field_name", f"field_{idx}"))
        field_type = goal.get("type", "string")
        question = goal.get("question", "")
        required = goal.get("required", False)

        parts = [f"  {idx}. **{name}** (type: {field_type})"]
        if question:
            parts.append(f"     Question: {question}")
        if required:
            parts.append("     Required: yes")

        goal_descriptions.append("\n".join(parts))

    goals_block = "\n".join(goal_descriptions)

    return (
        "You are analysing a phone call transcript. Extract the requested "
        "data fields from the conversation.\n\n"
        "## Transcript\n\n"
        f"{transcript}\n\n"
        "## Fields to extract\n\n"
        f"{goals_block}\n\n"
        "## Instructions\n\n"
        "For each field:\n"
        "1. Find the most relevant passage in the transcript.\n"
        "2. Extract the value (use null if not found).\n"
        "3. Assign a confidence score between 0.0 and 1.0.\n"
        "4. Include a short transcript quote that supports the value.\n\n"
        "Return JSON with a single key `fields` containing an array of "
        "objects, each with keys: `field_name`, `value`, `confidence`, "
        "`transcript_reference`."
    )


def _build_schema_hint(goals: list[dict]) -> str:
    """Return a JSON-schema hint string for generate_structured."""
    field_example = {
        "field_name": "string",
        "value": "any",
        "confidence": "number (0-1)",
        "transcript_reference": "string",
    }
    return json.dumps(
        {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": field_example,
                }
            },
        },
        indent=2,
    )


def _validate_extraction(field: dict, value: Any) -> bool:
    """Validate an extracted value against its field type and constraints."""
    field_type = field.get("type", "string").lower()

    expected_types = _FIELD_TYPE_VALIDATORS.get(field_type)
    if expected_types is not None and not isinstance(value, expected_types):
        if field_type in ("number", "integer", "float", "currency", "percentage"):
            try:
                float(value)
            except (TypeError, ValueError):
                return False
        else:
            return False

    options = field.get("options")
    if options and value not in options:
        if isinstance(value, str):
            lower_options = [str(o).lower() for o in options]
            if value.lower() not in lower_options:
                return False
        else:
            return False

    return True


def _find_goal_spec(
    field_name: str, goals: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Find the goal spec whose name matches *field_name*."""
    for goal in goals:
        name = goal.get("name", goal.get("field_name", ""))
        if name == field_name:
            return goal
    for goal in goals:
        name = goal.get("name", goal.get("field_name", ""))
        if name.lower() == field_name.lower():
            return goal
    return None


def _compute_overall_confidence(fields: list[dict[str, Any]]) -> float:
    """Average confidence across all fields that have a value."""
    scored = [f["confidence"] for f in fields if f.get("value") is not None]
    if not scored:
        return 0.0
    return round(sum(scored) / len(scored), 4)


def _compute_quality_score(
    fields: list[dict[str, Any]], goals: list[dict[str, Any]]
) -> float:
    """Fraction of required goals that were successfully extracted."""
    required_names: list[str] = []
    for goal in goals:
        if goal.get("required", False):
            required_names.append(goal.get("name", goal.get("field_name", "")))

    if not required_names:
        required_names = [
            goal.get("name", goal.get("field_name", "")) for goal in goals
        ]

    if not required_names:
        return 0.0

    extracted_names = {
        f["field_name"]
        for f in fields
        if f.get("value") is not None
        and f.get("confidence", 0) >= _MIN_FINDING_CONFIDENCE
    }

    matched = sum(1 for name in required_names if name in extracted_names)
    return round(matched / len(required_names), 4)


def _finding_type_for_field(field_name: str) -> FindingType:
    """Map field name to FindingType enum value."""
    lower = field_name.lower()
    if any(kw in lower for kw in ("price", "cost", "revenue", "salary", "budget")):
        return FindingType.price
    if any(kw in lower for kw in ("available", "availability", "slot", "open")):
        return FindingType.availability
    if any(kw in lower for kw in ("risk", "concern", "issue", "problem")):
        return FindingType.risk
    if any(kw in lower for kw in ("opportunity", "growth", "potential")):
        return FindingType.opportunity
    if any(kw in lower for kw in ("trend", "pattern", "change")):
        return FindingType.trend
    if any(kw in lower for kw in ("quote", "said", "mentioned")):
        return FindingType.quote
    if any(kw in lower for kw in ("contact", "email", "phone", "address")):
        return FindingType.contact_info
    if any(kw in lower for kw in ("sentiment", "feeling", "opinion")):
        return FindingType.sentiment
    if any(kw in lower for kw in ("count", "number", "total", "rate", "percent")):
        return FindingType.statistic
    return FindingType.data_point


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp *value* to the range [lo, hi]."""
    return max(lo, min(hi, value))
