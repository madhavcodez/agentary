"""Contact duplicate detection using fuzzy matching.

Prevents duplicate contacts from being created during research
by checking for exact email matches and fuzzy name+company
similarity using rapidfuzz.
"""

from __future__ import annotations

import re

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from ..models.contact import Contact


def _normalize(s: str) -> str:
    """Strip non-alpha characters and lowercase for comparison."""
    return re.sub(r"[^a-z]", "", s.lower())


def find_duplicates(
    db: Session,
    name: str,
    company: str,
    email: str | None = None,
    threshold: int = 85,
    user_id: str | None = None,
) -> list[Contact]:
    """Find potential duplicate contacts using multi-stage matching.

    Stage 1: Exact email match (strongest signal).
    Stage 2: Fuzzy name+company via token_sort_ratio.

    Args:
        db: Active database session.
        name: Contact name to check.
        company: Company name to check.
        email: Optional email for exact matching.
        threshold: Fuzzy match score threshold (0-100).
        user_id: Optional user_id to scope the search.

    Returns:
        List of existing Contact records that are potential duplicates.
    """
    duplicates: list[Contact] = []
    seen_ids: set[str] = set()

    # Stage 1: Exact email match
    if email:
        query = db.query(Contact).filter(Contact.email == email)
        if user_id:
            query = query.filter(Contact.user_id == user_id)

        email_matches = query.all()
        for contact in email_matches:
            contact_id = str(contact.id)
            if contact_id not in seen_ids:
                duplicates.append(contact)
                seen_ids.add(contact_id)

    # Stage 2: Fuzzy name+company matching
    query = db.query(Contact).filter(Contact.company.isnot(None))
    if user_id:
        query = query.filter(Contact.user_id == user_id)

    candidates = query.all()
    norm_name = _normalize(name)
    norm_company = _normalize(company)

    for contact in candidates:
        contact_id = str(contact.id)
        if contact_id in seen_ids:
            continue

        contact_name = _normalize(contact.name or "")
        contact_company = _normalize(contact.company or "")

        if not contact_name or not contact_company:
            continue

        name_score = fuzz.token_sort_ratio(norm_name, contact_name)
        company_score = fuzz.token_sort_ratio(norm_company, contact_company)

        # Both name and company must meet the threshold
        if name_score >= threshold and company_score >= threshold:
            duplicates.append(contact)
            seen_ids.add(contact_id)

    return duplicates
