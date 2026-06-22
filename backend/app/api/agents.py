from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.expert_agent import ExpertAgent
from ..models.user import User
from ..schemas.expert_agent import ExpertAgentResponse

router = APIRouter(prefix="/api/expert-agents", tags=["agents"])


@router.get("", response_model=list[ExpertAgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return db.query(ExpertAgent).filter(ExpertAgent.is_active.is_(True)).all()
