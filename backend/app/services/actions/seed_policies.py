"""Seed default action policies for a user."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.action_policy import ActionPolicy
from .policy_engine import DEFAULT_POLICIES

logger = logging.getLogger(__name__)


def seed_default_policies(db: Session, user_id: UUID) -> int:
    """Create default policies for a user if they don't exist. Returns count created."""
    existing = db.query(ActionPolicy).filter_by(user_id=user_id).count()
    if existing > 0:
        return 0

    count = 0
    for action_type, config in DEFAULT_POLICIES.items():
        auto = config.get("auto_approve", False)
        threshold = config.get("confidence_threshold")

        condition: dict = {"action_type": action_type}
        if threshold:
            condition["confidence_above"] = threshold

        policy = ActionPolicy(
            user_id=user_id,
            name=f"Default: {action_type}",
            description=f"Default policy for {action_type} actions",
            rules=[
                {
                    "condition": condition,
                    "result": {
                        "auto_approve": auto,
                        "require_approval": not auto,
                    },
                }
            ],
            is_active=True,
            priority=0,
        )
        db.add(policy)
        count += 1

    db.flush()
    return count
