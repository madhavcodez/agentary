"""Telemetry helpers for STORM pipeline runs.

Thin wrapper that writes a ``StormRun`` row at the end of a mission,
capturing counts, budget use, fallback reason, and the IDs that link
outline + report + crew_run together for post-hoc analysis.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def record_storm_run(
    *,
    db: Session,
    mission_id: Any,
    crew_run_id: Any | None,
    outline: Any | None,
    report: Any | None,
    status: str,
    fallback_reason: str | None,
    budget: Any | None,
    refinement_passes: int = 0,
    duration_ms: int | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> None:
    """Persist a ``StormRun`` row. Never raises — telemetry is best-effort."""
    from ...models.storm_run import StormRun

    perspectives = len((outline.perspectives or [])) if outline else 0
    questions = len((outline.question_matrix or [])) if outline else 0
    sections = len((outline.sections or [])) if outline else 0
    citations = 0
    sections_with_evidence = 0
    if report is not None:
        for s in (report.sections or []) or []:
            if s.get("content_md"):
                sections_with_evidence += 1
            citations += len(s.get("finding_ids_used") or [])

    flash = budget.flash_calls if budget else 0
    pro = budget.pro_calls if budget else 0

    try:
        row = StormRun(
            mission_id=mission_id,
            crew_run_id=crew_run_id,
            outline_id=(outline.id if outline else None),
            report_id=(report.id if report else None),
            status=status,
            fallback_reason=fallback_reason,
            perspectives_count=perspectives,
            questions_count=questions,
            sections_count=sections,
            sections_with_evidence=sections_with_evidence,
            citations_count=citations,
            refinement_passes=refinement_passes,
            flash_calls=flash,
            pro_calls=pro,
            duration_ms=duration_ms,
            meta=extra_meta or {},
        )
        db.add(row)
        db.commit()
    except Exception as exc:  # pragma: no cover — telemetry must not crash runs
        logger.warning("record_storm_run failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
