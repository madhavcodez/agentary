from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.source import Source
from ..models.user import User
from ..schemas.source import SourceResponse

router = APIRouter(prefix="/api/sources", tags=["sources"])


@router.get("", response_model=list[SourceResponse])
def list_sources(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(Source).filter(
        (Source.user_id == user.id) | (Source.is_system.is_(True))
    ).all()
