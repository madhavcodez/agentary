from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.dataset import DataSet
from ..models.user import User
from ..schemas.dataset import DataSetCreate, DataSetResponse

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("", response_model=DataSetResponse, status_code=201)
def create_dataset(
    body: DataSetCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    ds = DataSet(**body.model_dump())
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


@router.get("", response_model=list[DataSetResponse])
def list_datasets(
    project_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(DataSet)
    if project_id:
        query = query.filter(DataSet.project_id == project_id)
    return query.order_by(DataSet.created_at.desc()).all()
