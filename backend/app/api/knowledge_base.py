from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models.knowledge_base import KnowledgeBase
from ..models.user import User
from ..schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseResponse, KnowledgeBaseUpdate

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge_base"])


@router.post("", response_model=KnowledgeBaseResponse, status_code=201)
def create_kb(
    body: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kb = KnowledgeBase(user_id=user.id, **body.model_dump())
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


@router.get("", response_model=list[KnowledgeBaseResponse])
def list_kbs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(KnowledgeBase).filter(KnowledgeBase.user_id == user.id).all()


@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
def update_kb(
    kb_id: UUID,
    body: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id, KnowledgeBase.user_id == user.id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(kb, key, value)
    db.commit()
    db.refresh(kb)
    return kb
