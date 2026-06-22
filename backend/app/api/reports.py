"""Report generation, management, and export API routes."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.report import Report
from ..models.user import User
from ..schemas.report import (
    RegenerateSection,
    ReportCreate,
    ReportFull,
    ReportList,
    ReportSummary,
    ReportUpdate,
    ShareResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


def _report_to_full(r: Report) -> dict:
    return {
        "id": str(r.id),
        "user_id": str(r.user_id),
        "project_id": str(r.project_id) if r.project_id else None,
        "mission_id": str(r.mission_id) if r.mission_id else None,
        "title": r.title,
        "description": r.description,
        "report_type": r.report_type,
        "status": r.status,
        "content_markdown": r.content_markdown,
        "content_html": r.content_html,
        "sections": r.sections,
        "executive_summary": r.executive_summary,
        "methodology": r.methodology,
        "sources": r.sources,
        "charts": r.charts,
        "structured_data": r.structured_data,
        "metadata": r.metadata_,
        "format_config": r.format_config,
        "share_token": r.share_token,
        "share_enabled": r.share_enabled,
        "pdf_url": r.pdf_url,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def _report_to_summary(r: Report) -> dict:
    return {
        "id": str(r.id),
        "user_id": str(r.user_id),
        "project_id": str(r.project_id) if r.project_id else None,
        "mission_id": str(r.mission_id) if r.mission_id else None,
        "title": r.title,
        "description": r.description,
        "report_type": r.report_type,
        "status": r.status,
        "share_enabled": r.share_enabled,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def _run_report_generation(report_id: str, mission_id: str, report_type: str, config: dict | None):
    from ..database import SessionLocal
    from ..services.reports.report_generator import ReportGenerator

    db = SessionLocal()
    try:
        generator = ReportGenerator()
        generator.generate_report(
            mission_id=UUID(mission_id),
            report_type=report_type,
            config=config,
            db=db,
        )
    except Exception:
        logger.exception("Report generation failed for report_id=%s", report_id)
        report = db.query(Report).filter(Report.id == UUID(report_id)).first()
        if report:
            report.status = "failed"
            db.commit()
    finally:
        db.close()


@router.post("/", response_model=ReportFull)
def create_report(
    body: ReportCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..models.mission import Mission

    mission = (
        db.query(Mission)
        .filter(
            Mission.id == UUID(body.mission_id),
            Mission.user_id == user.id,
        )
        .first()
    )
    if not mission:
        raise HTTPException(404, "Mission not found")

    report = Report(
        user_id=user.id,
        mission_id=mission.id,
        project_id=mission.project_id,
        title=f"{body.report_type.replace('_', ' ').title()} — {mission.title}",
        report_type=body.report_type,
        status="generating",
        format_config=body.config,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background_tasks.add_task(
        _run_report_generation,
        str(report.id),
        str(mission.id),
        body.report_type,
        body.config,
    )
    return ReportFull(**_report_to_full(report))


@router.get("/", response_model=ReportList)
def list_reports(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    project_id: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Report).filter(Report.user_id == user.id)
    if project_id:
        query = query.filter(Report.project_id == UUID(project_id))
    total = query.count()
    reports = query.order_by(Report.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return ReportList(
        items=[ReportSummary(**_report_to_summary(r)) for r in reports],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/{report_id}", response_model=ReportFull)
def get_report(
    report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    report = (
        db.query(Report).filter(Report.id == UUID(report_id), Report.user_id == user.id).first()
    )
    if not report:
        raise HTTPException(404, "Report not found")
    return ReportFull(**_report_to_full(report))


@router.put("/{report_id}", response_model=ReportFull)
def update_report(
    report_id: str,
    body: ReportUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report).filter(Report.id == UUID(report_id), Report.user_id == user.id).first()
    )
    if not report:
        raise HTTPException(404, "Report not found")
    if body.title is not None:
        report.title = body.title
    if body.description is not None:
        report.description = body.description
    db.commit()
    db.refresh(report)
    return ReportFull(**_report_to_full(report))


@router.delete("/{report_id}")
def delete_report(
    report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    report = (
        db.query(Report).filter(Report.id == UUID(report_id), Report.user_id == user.id).first()
    )
    if not report:
        raise HTTPException(404, "Report not found")
    db.delete(report)
    db.commit()
    return {"status": "deleted"}


@router.post("/{report_id}/regenerate", response_model=ReportFull)
def regenerate_report(
    report_id: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = (
        db.query(Report).filter(Report.id == UUID(report_id), Report.user_id == user.id).first()
    )
    if not report:
        raise HTTPException(404, "Report not found")
    report.status = "generating"
    db.commit()
    background_tasks.add_task(
        _run_report_generation,
        str(report.id),
        str(report.mission_id),
        report.report_type,
        report.format_config,
    )
    db.refresh(report)
    return ReportFull(**_report_to_full(report))


@router.post("/{report_id}/regenerate-section", response_model=ReportFull)
def regenerate_section(
    report_id: str,
    body: RegenerateSection,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from ..services.reports.report_generator import ReportGenerator

    report = (
        db.query(Report).filter(Report.id == UUID(report_id), Report.user_id == user.id).first()
    )
    if not report:
        raise HTTPException(404, "Report not found")
    generator = ReportGenerator()
    updated = generator.regenerate_section(
        report_id=UUID(report_id),
        section_index=body.section_index,
        instructions=body.instructions,
        db=db,
    )
    return ReportFull(**_report_to_full(updated))


@router.get("/{report_id}/pdf")
def download_pdf(
    report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from ..services.reports.pdf_exporter import PDFExporter

    report = (
        db.query(Report).filter(Report.id == UUID(report_id), Report.user_id == user.id).first()
    )
    if not report:
        raise HTTPException(404, "Report not found")
    if report.status != "ready":
        raise HTTPException(400, "Report is not ready yet")
    exporter = PDFExporter()
    pdf_bytes = exporter.export_to_pdf(report)
    filename = f"{report.title[:60].replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/html")
def download_html(
    report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from ..services.reports.pdf_exporter import PDFExporter

    report = (
        db.query(Report).filter(Report.id == UUID(report_id), Report.user_id == user.id).first()
    )
    if not report:
        raise HTTPException(404, "Report not found")
    exporter = PDFExporter()
    html = exporter.export_to_html(report)
    return Response(content=html, media_type="text/html")


@router.get("/{report_id}/markdown")
def download_markdown(
    report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from ..services.reports.pdf_exporter import PDFExporter

    report = (
        db.query(Report).filter(Report.id == UUID(report_id), Report.user_id == user.id).first()
    )
    if not report:
        raise HTTPException(404, "Report not found")
    exporter = PDFExporter()
    md = exporter.export_to_markdown(report)
    filename = f"{report.title[:60].replace(' ', '_')}.md"
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{report_id}/share", response_model=ShareResponse)
def create_share_link(
    report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from ..services.reports.share_service import ShareService

    svc = ShareService()
    result = svc.create_share_link(UUID(report_id), user.id, db)
    return ShareResponse(**result)


@router.delete("/{report_id}/share")
def revoke_share(
    report_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    from ..services.reports.share_service import ShareService

    svc = ShareService()
    svc.revoke_share(UUID(report_id), user.id, db)
    return {"status": "share_revoked"}
