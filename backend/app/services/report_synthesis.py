"""Service layer for synthesizing reports from mission findings."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models.finding import Finding
from ..models.mission import Mission
from ..models.report import Report
from ..prompts.reports import build_report_prompt, REPORT_SCHEMA_HINT

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
