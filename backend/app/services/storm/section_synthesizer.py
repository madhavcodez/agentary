"""Per-section report synthesis with validated citations.

One Gemini Pro call per section. The prompt supplies only the bound
findings for that section (not all 50) and requires a citation list in
the response. The post-validation step rejects any citation whose
``finding_id`` is not in the bound set — hallucinated IDs don't make it
into the database.

Returns a ``SectionDraft`` dataclass that the caller (typically
``report_synthesis.synthesize_report_from_outline``) persists alongside
``SectionCitation`` rows.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Sequence

from ...prompts.storm import (
    SECTION_SCHEMA_HINT,
    build_refinement_prompt,
    build_section_prompt,
)
from .budget import StormBudget

logger = logging.getLogger(__name__)

# Model used for section-level synthesis. Pro variant only; the rest of
# the STORM pipeline uses Flash.
SECTION_MODEL = "gemini-2.5-pro"


@dataclass
class ValidatedCitation:
    finding_id: str
    quote_span: str | None
    confidence: float | None


@dataclass
class SectionDraft:
    section_index: int
    title: str
    content_md: str
    citations: list[ValidatedCitation]
    partial_evidence: bool = False
    refinement_passes: int = 0
    quality_verdict: str | None = None
    bound_findings_used: list[str] = field(default_factory=list)


async def synthesize_section(
    *,
    section: dict[str, Any],
    bound_findings: Sequence[tuple[Any, float]],
    budget: StormBudget,
) -> SectionDraft | None:
    """Draft one section with post-validated citations.

    ``bound_findings`` is the output of
    :func:`evidence_binder.bind_findings_to_sections` for this section — a
    list of ``(Finding, score)`` tuples.

    Returns ``None`` when the section has no bound evidence; caller
    decides whether to skip or flag for refinement. Raises
    :class:`StormBudgetExceeded` via ``budget.inc("pro")``.
    """
    from ..gemini import generate_structured

    if not bound_findings:
        logger.info(
            "section_synthesizer: section %d has 0 bound findings — skipping synthesis",
            section.get("index", 0),
        )
        return None

    findings_for_prompt = [f for (f, _score) in bound_findings]
    allowed_ids = {str(f.id) for f in findings_for_prompt}

    prompt = build_section_prompt(
        section_title=section.get("title", ""),
        section_scope=section.get("scope", ""),
        expected_evidence_types=section.get("expected_evidence_types") or [],
        bound_findings=findings_for_prompt,
    )

    draft = await _synthesize_once(
        prompt=prompt,
        allowed_ids=allowed_ids,
        budget=budget,
    )
    if draft is None:
        return None

    draft.section_index = int(section.get("index", 0))
    draft.title = section.get("title", "")
    draft.bound_findings_used = [str(f.id) for (f, _s) in bound_findings]
    return draft


async def refine_section(
    *,
    previous: SectionDraft,
    section: dict[str, Any],
    bound_findings: Sequence[tuple[Any, float]],
    quality_verdict: str,
    budget: StormBudget,
) -> SectionDraft | None:
    """Re-synthesize a section using the refinement prompt.

    Increments ``previous.refinement_passes`` on success. Caller enforces
    the global per-report refinement cap (see ``refinement.py``).
    """
    if not bound_findings:
        return None

    findings_for_prompt = [f for (f, _s) in bound_findings]
    allowed_ids = {str(f.id) for f in findings_for_prompt}

    prompt = build_refinement_prompt(
        section_title=section.get("title", ""),
        section_scope=section.get("scope", ""),
        previous_content_md=previous.content_md,
        quality_verdict=quality_verdict,
        bound_findings=findings_for_prompt,
    )

    draft = await _synthesize_once(
        prompt=prompt,
        allowed_ids=allowed_ids,
        budget=budget,
    )
    if draft is None:
        return previous

    draft.section_index = previous.section_index
    draft.title = previous.title
    draft.bound_findings_used = [str(f.id) for (f, _s) in bound_findings]
    draft.refinement_passes = previous.refinement_passes + 1
    draft.quality_verdict = quality_verdict
    return draft


async def _synthesize_once(
    *,
    prompt: str,
    allowed_ids: set[str],
    budget: StormBudget,
) -> SectionDraft | None:
    """One Pro call with post-validation. Single retry on schema violation."""
    from ..gemini import generate_structured

    for attempt in (1, 2):
        budget.inc("pro")
        try:
            result = await generate_structured(
                prompt, schema_hint=SECTION_SCHEMA_HINT, model=SECTION_MODEL
            )
        except TypeError:
            # generate_structured may not yet accept a model kwarg in older
            # revisions — fall back to default model (Flash). The call still
            # counts against the pro budget because the intent was Pro.
            result = await generate_structured(
                prompt, schema_hint=SECTION_SCHEMA_HINT
            )
        except Exception as exc:
            logger.warning(
                "section_synthesizer: generate_structured failed on attempt %d: %s",
                attempt,
                exc,
            )
            return None

        content_md = (result.get("content_md") or "").strip()
        raw_citations = result.get("citations") or []
        validated, rejected = _validate_citations(raw_citations, allowed_ids)

        # Retry once with stricter prompt if no citation was valid and the
        # attempt is 1; otherwise accept partial evidence or return None.
        if not validated and rejected and attempt == 1:
            logger.info(
                "section_synthesizer: all %d citations rejected on attempt 1 — retrying with stricter hint",
                len(rejected),
            )
            prompt = (
                prompt
                + "\n\nCRITICAL: Your previous attempt cited finding_ids that do "
                "not appear in the bound_findings list. You MUST use exact ids "
                "from the <finding id=\"...\"> attributes above. No other ids are valid."
            )
            continue

        if not content_md:
            return None

        return SectionDraft(
            section_index=0,  # filled by caller
            title="",
            content_md=content_md,
            citations=validated,
            partial_evidence=bool(rejected) and bool(validated),
        )

    return None


def _validate_citations(
    raw: list[Any], allowed_ids: set[str]
) -> tuple[list[ValidatedCitation], list[dict[str, Any]]]:
    validated: list[ValidatedCitation] = []
    rejected: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        fid = str(item.get("finding_id") or "").strip()
        if not fid or fid not in allowed_ids:
            rejected.append(item)
            continue
        validated.append(
            ValidatedCitation(
                finding_id=fid,
                quote_span=(item.get("quote_span") or None),
                confidence=_coerce_confidence(item.get("confidence")),
            )
        )
    return validated, rejected


def _coerce_confidence(raw: Any) -> float | None:
    if raw is None:
        return None
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return None
    if v < 0.0:
        return 0.0
    if v > 1.0:
        return 1.0
    return v
