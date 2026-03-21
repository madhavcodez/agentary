from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..deps import get_db, get_current_user
from ..models.user import User
from ..models.expert_agent import ExpertAgent
from ..schemas.expert_agent import ExpertAgentResponse

router = APIRouter(prefix="/api/expert-agents", tags=["agents"])


@router.get("", response_model=list[ExpertAgentResponse])
def list_agents(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return db.query(ExpertAgent).filter(ExpertAgent.is_active == True).all()
