from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models.contact import Contact
from ..schemas.contact import ContactCreate, ContactList, ContactResponse, ContactUpdate

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=ContactList)
def list_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    company: str | None = None,
    db: Session = Depends(get_db),
):
    """List contacts with optional company filter and pagination."""
    query = db.query(Contact)

    if company:
        query = query.filter(Contact.company.ilike(f"%{company}%"))

    total = query.count()
    items = (
        query.order_by(Contact.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return ContactList(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=ContactResponse, status_code=201)
def create_contact(body: ContactCreate, db: Session = Depends(get_db)):
    """Create a new contact."""
    contact = Contact(**body.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: UUID, db: Session = Depends(get_db)):
    """Get a single contact by ID."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: UUID, body: ContactUpdate, db: Session = Depends(get_db)
):
    """Update an existing contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=204)
def delete_contact(contact_id: UUID, db: Session = Depends(get_db)):
    """Delete a contact."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
