"""Core action request lifecycle management."""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ...core.events import Event, EventType, event_bus
from ...models.action_request import ActionRequest, ActionRequestStatus, ActionType

logger = logging.getLogger(__name__)


class ActionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_action_request(
        self,
        project_id: UUID,
        user_id: UUID,
        action_type: str,
        title: str,
        description: str | None = None,
        parameters: dict | None = None,
        recommendation_id: UUID | None = None,
        entity_id: UUID | None = None,
        confidence: float = 1.0,
        priority: str = "medium",
    ) -> ActionRequest:
        from .policy_engine import PolicyEngine

        action = ActionRequest(
            project_id=project_id,
            user_id=user_id,
            action_type=ActionType(action_type),
            title=title,
            description=description,
            parameters=parameters or {},
            recommendation_id=recommendation_id,
            entity_id=entity_id,
            confidence=confidence,
            priority=priority,
        )
        self.db.add(action)
        self.db.flush()

        # Evaluate policy
        engine = PolicyEngine(self.db)
        decision = engine.evaluate(action)
        action.requires_approval = decision["requires_approval"]
        action.policy_id = decision.get("policy_id")

        if decision.get("auto_approve"):
            action.status = ActionRequestStatus.approved
            action.approved_at = datetime.now(UTC)
            self._append_transition(action, "pending_approval", "approved", "auto-approved by policy")
            self.db.flush()
            # Dispatch execution
            self._dispatch_execution(action)
        else:
            action.status = ActionRequestStatus.pending_approval
            self._append_transition(action, None, "pending_approval", "awaiting approval per policy")
            self.db.flush()
            # Emit pending event
            self._emit_event("action.pending_approval", action)

        return action

    def approve(self, action_id: UUID, approved_by: UUID) -> ActionRequest:
        action = self.db.query(ActionRequest).filter_by(id=action_id).first()
        if not action:
            raise ValueError(f"ActionRequest {action_id} not found")
        if action.status != ActionRequestStatus.pending_approval:
            raise ValueError(f"Cannot approve action in status {action.status}")

        action.status = ActionRequestStatus.approved
        action.approved_by = approved_by
        action.approved_at = datetime.now(UTC)
        self._append_transition(action, "pending_approval", "approved", f"approved by user {approved_by}")
        self.db.flush()

        self._dispatch_execution(action)
        self._emit_event("action.approved", action)
        return action

    def reject(self, action_id: UUID, rejected_by: UUID, reason: str) -> ActionRequest:
        action = self.db.query(ActionRequest).filter_by(id=action_id).first()
        if not action:
            raise ValueError(f"ActionRequest {action_id} not found")
        if action.status != ActionRequestStatus.pending_approval:
            raise ValueError(f"Cannot reject action in status {action.status}")

        action.status = ActionRequestStatus.rejected
        self._append_transition(action, "pending_approval", "rejected", reason)
        self.db.flush()

        return action

    def cancel(self, action_id: UUID) -> ActionRequest:
        action = self.db.query(ActionRequest).filter_by(id=action_id).first()
        if not action:
            raise ValueError(f"ActionRequest {action_id} not found")
        terminal = (ActionRequestStatus.completed, ActionRequestStatus.failed, ActionRequestStatus.cancelled)
        if action.status in terminal:
            raise ValueError(f"Cannot cancel action in terminal status {action.status}")

        prev = action.status.value if hasattr(action.status, "value") else str(action.status)
        action.status = ActionRequestStatus.cancelled
        self._append_transition(action, prev, "cancelled", "cancelled by user")
        self.db.flush()
        return action

    def get_pending(self, user_id: UUID, project_id: UUID | None = None) -> list[ActionRequest]:
        q = self.db.query(ActionRequest).filter(
            ActionRequest.user_id == user_id,
            ActionRequest.status == ActionRequestStatus.pending_approval,
        )
        if project_id:
            q = q.filter(ActionRequest.project_id == project_id)
        return q.order_by(ActionRequest.created_at.asc()).all()

    def list_actions(
        self,
        project_id: UUID | None = None,
        status: str | None = None,
        action_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ActionRequest]:
        q = self.db.query(ActionRequest)
        if project_id:
            q = q.filter(ActionRequest.project_id == project_id)
        if status:
            q = q.filter(ActionRequest.status == status)
        if action_type:
            q = q.filter(ActionRequest.action_type == action_type)
        return q.order_by(ActionRequest.created_at.desc()).offset(offset).limit(limit).all()

    def _append_transition(
        self, action: ActionRequest, from_state: str | None, to_state: str, reason: str
    ) -> None:
        transitions = list(action.state_transitions or [])
        transitions.append({
            "from": from_state,
            "to": to_state,
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": reason,
        })
        action.state_transitions = transitions

    def _dispatch_execution(self, action: ActionRequest) -> None:
        try:
            from ...tasks.action_tasks import dispatch_action

            dispatch_action.delay(str(action.id))
        except Exception:
            logger.warning("Could not dispatch action %s to Celery, will need manual execution", action.id)

    def _emit_event(self, event_type_str: str, action: ActionRequest) -> None:
        try:
            et = EventType(event_type_str)
            event = Event(
                event_type=et,
                data={
                    "action_id": str(action.id),
                    "action_type": action.action_type.value if hasattr(action.action_type, "value") else str(action.action_type),
                    "title": action.title,
                    "status": action.status.value if hasattr(action.status, "value") else str(action.status),
                    "priority": action.priority,
                },
                project_id=action.project_id,
                user_id=action.user_id,
            )
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(event_bus.broadcast(event))
            except RuntimeError:
                pass
        except Exception:
            pass
