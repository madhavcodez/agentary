"""Public shared report endpoint — NO AUTH REQUIRED."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..schemas.report import ReportFull

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/shared", tags=["shared"])


@router.get("/reports/{token}", response_model=ReportFull)
def get_shared_report(
    token: str,
    db: Session = Depends(get_db),
):
    """View a shared report. No authentication required."""
    from ..services.reports.share_service import ShareService

    svc = ShareService()
    report = svc.get_shared_report(token, db)
    if not report:
        raise HTTPException(404, "Report not found or sharing is disabled")

    return ReportFull(
        id=str(report.id),
        user_id=str(report.user_id),
        project_id=str(report.project_id) if report.project_id else None,
        mission_id=str(report.mission_id) if report.mission_id else None,
        title=report.title,
        description=report.description,
        report_type=report.report_type,
        status=report.status,
        content_markdown=report.content_markdown,
        content_html=report.content_html,
        sections=report.sections,
        executive_summary=report.executive_summary,
        methodology=report.methodology,
        sources=report.sources,
        charts=report.charts,
        structured_data=report.structured_data,
        metadata=report.metadata_,
        format_config=report.format_config,
        share_token=None,  # Don't expose token in response
        share_enabled=report.share_enabled,
        pdf_url=report.pdf_url,
        created_at=report.created_at,
        updated_at=report.updated_at,
    )
