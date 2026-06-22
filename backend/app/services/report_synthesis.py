"""Service layer for synthesizing reports from mission findings.

Two entry points:

* :func:`synthesize_report_from_findings` — legacy single-pass path: top-50
  findings by confidence → one Gemini call → Report. Kept for missions
  without an associated :class:`ResearchOutline`.

* :func:`synthesize_report_from_outline` — STORM path: binds findings to
  outline sections, synthesizes each section in parallel with Gemini Pro
  and validated citations, optionally runs the bounded refinement loop,
  and persists ``SectionCitation`` rows alongside the Report.

The public contract (``Report`` shape, ``status`` transitions, return
type) is identical for both paths so downstream consumers (dashboard
renderers, PDF export, share links) don't need to branch.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models.finding import Finding
from ..models.mission import Mission
from ..models.report import Report
from ..models.section_citation import SectionCitation
from ..prompts.reports import REPORT_SCHEMA_HINT, build_report_prompt

logger = logging.getLogger(__name__)


def _compile_sources(findings: list) -> list[dict]:
    """Deduplicate and compile source entries from findings."""
    seen_urls: set[str] = set()
    sources: list[dict] = []
    for f in findings:
        if not f.source_name and not f.source_url:
            continue
        key = f.source_url or f.source_name or ""
        if key in seen_urls:
            continue
        seen_urls.add(key)
        sources.append({
            "name": f.source_name or "Unknown",
            "url": f.source_url,
            "type": f.source_type.value if hasattr(f.source_type, "value") else str(f.source_type) if f.source_type else "unknown",
            "accessed_at": f.created_at.isoformat() if f.created_at else None,
        })
    return sources


def _parse_sections(raw: Any) -> list[dict]:
    """Normalize the sections array from Gemini response."""
    if not isinstance(raw, list):
        return []
    return [
        {
            "title": s.get("title", f"Section {i + 1}"),
            "content_md": s.get("content_md", ""),
            "finding_ids_used": [],
            "chart_configs": [],
            "order": i,
        }
        for i, s in enumerate(raw)
    ]


def _render_html(markdown: str) -> str:
    """Convert markdown to HTML. Returns empty string on failure."""
    if not markdown:
        return ""
    try:
        import markdown2
        return markdown2.markdown(
            markdown,
            extras=["tables", "fenced-code-blocks", "header-ids", "strike", "task_list"],
        )
    except Exception as exc:
        logger.warning("Markdown to HTML conversion failed: %s", exc)
        return ""


async def synthesize_report_from_findings(
    mission: Mission,
    user_id: Any,
    db: Session,
) -> Report:
    """Synthesize a report from mission findings using Gemini.

    Returns the created Report object (committed to DB).
    Raises ValueError if no findings exist.
    Raises RuntimeError if Gemini fails.
    """
    from ..services.gemini import generate_structured

    findings = (
        db.query(Finding)
        .filter(Finding.mission_id == mission.id)
        .order_by(Finding.confidence.desc())
        .limit(50)
        .all()
    )

    if not findings:
        raise ValueError("No findings available to synthesize a report")

    prompt = build_report_prompt(
        mission_name=mission.name,
        objective=mission.objective,
        findings=findings,
    )

    try:
        result = await generate_structured(prompt, schema_hint=REPORT_SCHEMA_HINT)
    except Exception as exc:
        logger.error("Gemini report synthesis failed for mission %s: %s", mission.id, exc)
        raise RuntimeError("AI report synthesis failed") from exc

    content_markdown = result.get("content_markdown", "")
    content_html = _render_html(content_markdown)
    sections = _parse_sections(result.get("sections", []))
    sources = _compile_sources(findings)

    report = Report(
        user_id=user_id,
        mission_id=mission.id,
        project_id=mission.project_id,
        title=result.get("title", f"Synthesized Report: {mission.name}"),
        description=f"AI-synthesized report from {len(findings)} findings",
        report_type="research_report",
        status="ready",
        content_markdown=content_markdown,
        content_html=content_html,
        sections=sections,
        executive_summary=result.get("executive_summary", ""),
        methodology=result.get("methodology", ""),
        sources=sources,
        metadata_={
            "total_findings": len(findings),
            "total_sources": len(sources),
            "synthesis_model": "gemini-2.5-flash",
        },
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return report


# ─── STORM synthesis path ────────────────────────────────────────────────
async def synthesize_report_from_outline(
    mission: Mission,
    outline: Any,
    user_id: Any,
    db: Session,
    *,
    enable_refinement: bool = True,
    section_concurrency: int = 3,
) -> Report:
    """Synthesize a report using a pre-planned STORM outline.

    Each outline section is bound to its own evidence subset (via
    embedding similarity), synthesized by Gemini Pro, and validated so
    that every citation references a real ``Finding.id`` in the bound
    set. ``SectionCitation`` rows are persisted alongside the Report.

    ``enable_refinement`` runs the bounded quality-gate loop; disable for
    tests or quick smoke runs.
    """
    from .storm.budget import StormBudget, StormBudgetExceeded
    from .storm.evidence_binder import bind_findings_to_sections
    from .storm.section_synthesizer import (
        SectionDraft,
        synthesize_section,
    )

    findings = (
        db.query(Finding)
        .filter(Finding.mission_id == mission.id)
        .order_by(Finding.confidence.desc())
        .limit(50)
        .all()
    )
    if not findings:
        raise ValueError("No findings available to synthesize a STORM report")

    sections = outline.sections or []
    if not sections:
        raise ValueError("Outline has no sections — cannot synthesize")

    # Evidence binding (deterministic, no LLM).
    bindings = await bind_findings_to_sections(
        sections=sections,
        findings=findings,
    )

    budget = StormBudget(mission_id=str(mission.id))

    async def _synth_one(section: dict[str, Any]) -> tuple[int, SectionDraft | None]:
        idx = int(section.get("index", 0))
        bound = bindings.get(idx, [])
        try:
            draft = await synthesize_section(
                section=section,
                bound_findings=bound,
                budget=budget,
            )
        except StormBudgetExceeded as exc:
            logger.warning(
                "synthesize_report_from_outline: budget exceeded at section %d: %s",
                idx,
                exc,
            )
            return idx, None
        return idx, draft

    semaphore = asyncio.Semaphore(section_concurrency)

    async def _bounded(section: dict[str, Any]) -> tuple[int, SectionDraft | None]:
        async with semaphore:
            return await _synth_one(section)

    results = await asyncio.gather(*[_bounded(s) for s in sections])
    drafts: dict[int, SectionDraft] = {
        idx: d for (idx, d) in results if d is not None
    }

    if enable_refinement and drafts:
        try:
            from .storm.refinement import refine_report_drafts

            drafts = await refine_report_drafts(
                drafts=drafts,
                sections=sections,
                bindings=bindings,
                budget=budget,
            )
        except StormBudgetExceeded as exc:
            logger.warning(
                "synthesize_report_from_outline: refinement budget exceeded: %s",
                exc,
            )
        except ImportError:
            # Phase 3 not installed yet — skip refinement
            logger.info("synthesize_report_from_outline: refinement module unavailable, skipping")

    # Compose the Report
    ordered_sections: list[dict[str, Any]] = []
    for section in sections:
        idx = int(section.get("index", 0))
        draft = drafts.get(idx)
        if draft is None:
            ordered_sections.append({
                "title": section.get("title", f"Section {idx + 1}"),
                "content_md": "",
                "finding_ids_used": [],
                "chart_configs": [],
                "order": idx,
                "skipped_no_evidence": True,
            })
            continue
        ordered_sections.append({
            "title": draft.title or section.get("title", f"Section {idx + 1}"),
            "content_md": draft.content_md,
            "finding_ids_used": [c.finding_id for c in draft.citations],
            "chart_configs": [],
            "order": idx,
            "partial_evidence": draft.partial_evidence,
            "refinement_passes": draft.refinement_passes,
        })

    content_markdown = _compose_markdown(outline.title, ordered_sections)
    content_html = _render_html(content_markdown)
    sources = _compile_sources(findings)

    report = Report(
        user_id=user_id,
        mission_id=mission.id,
        project_id=mission.project_id,
        title=outline.title or f"Research Report: {mission.name}",
        description=f"STORM-synthesized report from {len(findings)} findings across {len(sections)} sections",
        report_type="research_report",
        status="ready",
        content_markdown=content_markdown,
        content_html=content_html,
        sections=ordered_sections,
        executive_summary=_extract_executive_summary(ordered_sections),
        methodology=_storm_methodology_blurb(outline, budget),
        sources=sources,
        storm_generated=True,
        metadata_={
            "total_findings": len(findings),
            "total_sources": len(sources),
            "synthesis_model": "gemini-2.5-pro",
            "storm_version": 1,
            "outline_id": str(outline.id),
            "budget_flash_calls": budget.flash_calls,
            "budget_pro_calls": budget.pro_calls,
            "sections_total": len(sections),
            "sections_with_evidence": sum(
                1 for s in ordered_sections if not s.get("skipped_no_evidence")
            ),
        },
    )
    db.add(report)
    db.flush()  # need report.id for SectionCitation FKs

    for section in sections:
        idx = int(section.get("index", 0))
        draft = drafts.get(idx)
        if draft is None:
            continue
        for citation in draft.citations:
            db.add(
                SectionCitation(
                    report_id=report.id,
                    section_index=idx,
                    finding_id=citation.finding_id,
                    quote_span=citation.quote_span,
                    confidence=citation.confidence,
                )
            )

    db.commit()
    db.refresh(report)
    logger.info(
        "synthesize_report_from_outline: report %s produced (%d sections, %d citations, %d Pro calls)",
        report.id,
        len(drafts),
        sum(len(d.citations) for d in drafts.values()),
        budget.pro_calls,
    )
    return report


def _compose_markdown(title: str, ordered_sections: list[dict[str, Any]]) -> str:
    parts = [f"# {title}\n"]
    for section in ordered_sections:
        parts.append(f"## {section['title']}\n")
        body = section.get("content_md") or ""
        if not body and section.get("skipped_no_evidence"):
            parts.append("_Section skipped: no supporting evidence available._\n")
        else:
            parts.append(body.strip() + "\n")
    return "\n".join(parts)


def _extract_executive_summary(ordered_sections: list[dict[str, Any]]) -> str:
    """First 80 words of the first non-empty section — good-enough default."""
    for s in ordered_sections:
        body = (s.get("content_md") or "").strip()
        if body:
            words = body.split()
            return " ".join(words[:80])
    return ""


def _storm_methodology_blurb(outline: Any, budget: Any) -> str:
    return (
        "Generated via Stanford STORM-inspired pre-writing: "
        f"{len(outline.perspectives or [])} perspectives mined, "
        f"{len(outline.question_matrix or [])} questions generated, "
        f"{len(outline.sections or [])} sections planned. "
        "Each section was synthesized independently from a bound evidence "
        "subset; citations were post-validated against finding_ids to "
        "prevent hallucinated references. Gemini usage: "
        f"{budget.flash_calls} Flash (pre-write) + {budget.pro_calls} Pro (section synthesis)."
    )
