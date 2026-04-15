"""Bounded iterative refinement of STORM section drafts.

Uses purely structural quality metrics (citation density, coverage of
bound evidence, minimum length) rather than an LLM-as-judge — doubling
Gemini Pro spend just to critique yourself is the exact mistake that
killed DeerFlow on the politics briefing.

Global cap: the total number of refinement Pro calls per report is
bounded (default 2). Even if 5 sections fail the gate, only the 2
lowest-scoring are refined; the rest carry their partial_evidence flag
into the final report.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Sequence

logger = logging.getLogger(__name__)


# Thresholds — tune via config; defaults calibrated for 400-800 word sections.
DEFAULT_MIN_CITATION_DENSITY = 0.005  # citations per word (e.g., 1 per 200 words)
DEFAULT_MIN_COVERAGE = 0.4  # fraction of bound findings the section actually cited
DEFAULT_MIN_WORDS = 60
DEFAULT_MAX_REFINEMENT_PASSES = 2


@dataclass
class SectionQuality:
    section_index: int
    citation_density: float
    coverage: float
    word_count: int
    verdict: str  # "pass" | "refine" | "drop"
    reasons: list[str]


def evaluate_section(
    *,
    section_index: int,
    content_md: str,
    citations: Sequence[Any],
    bound_findings: Sequence[tuple[Any, float]],
    min_density: float = DEFAULT_MIN_CITATION_DENSITY,
    min_coverage: float = DEFAULT_MIN_COVERAGE,
    min_words: int = DEFAULT_MIN_WORDS,
) -> SectionQuality:
    """Score one section against structural thresholds. No LLM call."""
    words = _word_count(content_md)
    reasons: list[str] = []

    if words < min_words:
        reasons.append(f"too_short:{words}w<{min_words}w")

    density = (len(citations) / words) if words else 0.0
    if density < min_density:
        reasons.append(f"low_density:{density:.4f}<{min_density:.4f}")

    bound_ids = {str(f.id) for (f, _) in bound_findings}
    cited_ids = {c.finding_id for c in citations}
    used = cited_ids & bound_ids
    coverage = (len(used) / len(bound_ids)) if bound_ids else 0.0
    if bound_ids and coverage < min_coverage:
        reasons.append(f"low_coverage:{coverage:.2f}<{min_coverage:.2f}")

    if not reasons:
        verdict = "pass"
    elif not bound_ids:
        verdict = "drop"
    else:
        verdict = "refine"

    return SectionQuality(
        section_index=section_index,
        citation_density=density,
        coverage=coverage,
        word_count=words,
        verdict=verdict,
        reasons=reasons,
    )


def _word_count(md: str) -> int:
    if not md:
        return 0
    # Strip code fences and list markers for a sane word count
    cleaned = re.sub(r"```.*?```", "", md, flags=re.DOTALL)
    cleaned = re.sub(r"[#*`_\[\]()>-]", " ", cleaned)
    return len([w for w in cleaned.split() if w.strip()])


async def refine_report_drafts(
    *,
    drafts: dict[int, Any],
    sections: Sequence[dict[str, Any]],
    bindings: dict[int, list[tuple[Any, float]]],
    budget: Any,
    max_passes: int = DEFAULT_MAX_REFINEMENT_PASSES,
) -> dict[int, Any]:
    """Apply the quality gate and refine up to ``max_passes`` sections.

    Sections are sorted by worst verdict first (lowest coverage / density)
    so the budget is spent on sections that most need help. Returns the
    updated drafts dict (mutated copy); original drafts are preserved for
    sections that passed or were skipped.
    """
    from .section_synthesizer import refine_section

    if max_passes <= 0 or not drafts:
        return drafts

    scored: list[tuple[SectionQuality, Any, dict[str, Any]]] = []
    section_by_index = {int(s.get("index", 0)): s for s in sections}

    for idx, draft in drafts.items():
        section = section_by_index.get(idx)
        if section is None:
            continue
        bound = bindings.get(idx, [])
        q = evaluate_section(
            section_index=idx,
            content_md=draft.content_md,
            citations=draft.citations,
            bound_findings=bound,
        )
        if q.verdict == "pass":
            continue
        scored.append((q, draft, section))

    if not scored:
        logger.info("refinement: no sections need refinement")
        return drafts

    # Worst first: rank by (coverage asc, density asc)
    scored.sort(key=lambda t: (t[0].coverage, t[0].citation_density))

    refined_count = 0
    updated = dict(drafts)
    for q, draft, section in scored:
        if refined_count >= max_passes:
            logger.info(
                "refinement: global cap reached (%d); leaving %d sections at partial quality",
                max_passes,
                len(scored) - refined_count,
            )
            break
        if q.verdict == "drop":
            # No bound evidence — nothing to refine, leave as-is
            continue

        verdict_str = ", ".join(q.reasons)
        try:
            new_draft = await refine_section(
                previous=draft,
                section=section,
                bound_findings=bindings.get(q.section_index, []),
                quality_verdict=verdict_str,
                budget=budget,
            )
        except Exception as exc:
            logger.warning(
                "refinement: refine_section failed for index %d: %s",
                q.section_index,
                exc,
            )
            continue

        if new_draft is not None:
            updated[q.section_index] = new_draft
            refined_count += 1
            logger.info(
                "refinement: pass %d/%d applied to section %d (verdict=%s)",
                refined_count,
                max_passes,
                q.section_index,
                verdict_str,
            )

    logger.info(
        "refinement: %d of %d flagged sections refined",
        refined_count,
        len(scored),
    )
    return updated
