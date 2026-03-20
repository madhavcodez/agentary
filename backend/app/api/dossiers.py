from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.dossier import Dossier
from ..models.match import Match
from ..models.user import User
from ..schemas.dossier import DossierResponse

router = APIRouter(prefix="/matches", tags=["dossiers"])


@router.get("/{match_id}/dossier", response_model=DossierResponse)
def get_dossier(
    match_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    dossier = (
        db.query(Dossier)
        .filter(Dossier.match_id == match_id, Dossier.user_id == user.id)
        .first()
    )
    if not dossier:
        raise HTTPException(status_code=404, detail="Dossier not found. Generate one first.")
    return dossier


@router.post("/{match_id}/dossier", response_model=DossierResponse)
async def generate_dossier(
    match_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    match = (
        db.query(Match)
        .filter(Match.id == match_id, Match.user_id == user.id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    from ..services.dossier_gen import generate_dossier
    dossier = await generate_dossier(db, match, user_id=user.id)
    return dossier
