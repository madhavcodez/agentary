from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ..models.user import User
from ..models.report import Report
from ..schemas.report import ReportCreate, ReportResponse

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=201)
def create_report(
    body: ReportCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    report = Report(**body.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("", response_model=list[ReportResponse])
def list_reports(
    project_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(Report)
    if project_id:
        query = query.filter(Report.project_id == project_id)
    return query.order_by(Report.created_at.desc()).all()


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    from fastapi import HTTPException
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
