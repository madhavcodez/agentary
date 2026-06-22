"""Evaluate action policies to determine approval requirements."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ...models.action_policy import ActionPolicy
from ...models.action_request import ActionRequest

logger = logging.getLogger(__name__)

# Default policies when no DB policies match
DEFAULT_POLICIES: dict[str, dict] = {
    "update_status": {"auto_approve": True, "confidence_threshold": 0.8},
    "send_alert": {"auto_approve": True},
    "trigger_workflow": {"auto_approve": False},
    "trigger_monitor": {"auto_approve": True},
    "create_task": {"auto_approve": True},
    "generate_report": {"auto_approve": True},
    "send_digest": {"auto_approve": True},
    "queue_call": {"auto_approve": False},
    "merge_entities": {"auto_approve": False, "confidence_threshold": 0.9},
    "escalate": {"auto_approve": True},
    "custom": {"auto_approve": False},
}


class PolicyEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def evaluate(self, action: ActionRequest) -> dict:
        """Evaluate policies for an action request. Returns PolicyDecision dict."""
        action_type = (
            action.action_type.value
            if hasattr(action.action_type, "value")
            else str(action.action_type)
        )

        # 1. Check DB policies (user/project specific, sorted by priority desc)
        policies = (
            self.db.query(ActionPolicy)
            .filter(
                ActionPolicy.user_id == action.user_id,
                ActionPolicy.is_active == True,  # noqa: E712
            )
            .filter(
                (ActionPolicy.project_id == action.project_id) | (ActionPolicy.project_id.is_(None))
            )
            .order_by(ActionPolicy.priority.desc())
            .all()
        )

        for policy in policies:
            for rule in policy.rules or []:
                condition = rule.get("condition", {})
                result = rule.get("result", {})

                if self._matches_condition(condition, action, action_type):
                    return {
                        "requires_approval": result.get(
                            "require_approval", not result.get("auto_approve", False)
                        ),
                        "auto_approve": result.get("auto_approve", False),
                        "policy_id": str(policy.id),
                        "timeout_hours": result.get("timeout_hours"),
                        "escalate_to": result.get("escalate_to"),
                    }

        # 2. Fall back to default policies
        default = DEFAULT_POLICIES.get(action_type, {"auto_approve": False})
        auto = default.get("auto_approve", False)

        # Check confidence threshold if present
        threshold = default.get("confidence_threshold")
        if threshold and action.confidence < threshold:
            auto = False

        return {
            "requires_approval": not auto,
            "auto_approve": auto,
            "policy_id": None,
            "timeout_hours": None,
        }

    def _matches_condition(self, condition: dict, action: ActionRequest, action_type: str) -> bool:
        # action_type match
        cond_type = condition.get("action_type")
        if cond_type and cond_type != action_type:
            return False

        # confidence_above
        conf_above = condition.get("confidence_above")
        if conf_above is not None and action.confidence < conf_above:
            return False

        # priority_in
        priority_in = condition.get("priority_in")
        return not (priority_in and action.priority not in priority_in)
