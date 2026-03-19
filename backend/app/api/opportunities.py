from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models.opportunity import Opportunity
from ..schemas.opportunity import OpportunityList, OpportunityResponse

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=OpportunityList)
def list_opportunities(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    source: str | None = None,
    company: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Opportunity)

    if source:
        query = query.filter(Opportunity.source == source)
    if company:
        query = query.filter(Opportunity.company.ilike(f"%{company}%"))
    if search:
        query = query.filter(
            Opportunity.title.ilike(f"%{search}%") | Opportunity.description.ilike(f"%{search}%")
        )

    total = query.count()
    items = query.order_by(Opportunity.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return OpportunityList(items=items, total=total, page=page, limit=limit)


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(opportunity_id: UUID, db: Session = Depends(get_db)):
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp
