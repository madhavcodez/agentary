"""Action execution Celery tasks."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from ..celery_app import celery_app
from ..database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=1, soft_time_limit=300)
def dispatch_action(self, action_request_id: str) -> dict:
    """Execute an approved action request."""
    db = SessionLocal()
    try:
        from ..models.action_request import ActionRequest, ActionRequestStatus
        from ..models.action_execution import (
            ActionExecution,
            ExecutionStatus,
            ExecutorType,
        )
        from ..services.actions.handlers import get_handler, register_all_handlers

        register_all_handlers()

        action = db.query(ActionRequest).filter_by(id=action_request_id).first()
        if not action:
            return {"status": "error", "reason": "action_not_found"}

        if action.status not in (
            ActionRequestStatus.approved,
            ActionRequestStatus.executing,
        ):
            return {
                "status": "skipped",
                "reason": f"action in {action.status} state",
            }

        # Mark as executing
        action.status = ActionRequestStatus.executing
        transitions = list(action.state_transitions or [])
        transitions.append(
            {
                "from": "approved",
                "to": "executing",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": "dispatched to worker",
            }
        )
        action.state_transitions = transitions

        # Create execution record
        execution = ActionExecution(
            action_request_id=action.id,
            executor_type=ExecutorType.celery_worker,
            status=ExecutionStatus.running,
        )
        db.add(execution)
        db.flush()

        # Get handler
        action_type = (
            action.action_type.value
            if hasattr(action.action_type, "value")
            else str(action.action_type)
        )
        handler = get_handler(action_type)
        if not handler:
            execution.status = ExecutionStatus.failed
            execution.error = {
                "message": f"No handler for action type: {action_type}"
            }
            execution.completed_at = datetime.now(timezone.utc)
            action.status = ActionRequestStatus.failed
            transitions.append(
                {
                    "from": "executing",
                    "to": "failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": f"no handler for {action_type}",
                }
            )
            action.state_transitions = transitions
            db.commit()
            return {"status": "error", "reason": f"no handler for {action_type}"}

        # Execute handler
        try:
            result = asyncio.run(handler.execute(action, db))

            execution.status = ExecutionStatus.completed
            execution.result = result.get("result", {})
            execution.side_effects = result.get("side_effects", [])
            execution.completed_at = datetime.now(timezone.utc)

            action.status = ActionRequestStatus.completed
            transitions.append(
                {
                    "from": "executing",
                    "to": "completed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": "handler completed successfully",
                }
            )
            action.state_transitions = transitions

            db.commit()

            # Record outcome with feedback loop
            _record_outcome(db, action, execution, "success", result)

            return {"status": "completed", "action_id": action_request_id}

        except Exception as handler_error:
            logger.error(
                "Handler failed for action %s: %s",
                action_request_id,
                handler_error,
            )
            execution.status = ExecutionStatus.failed
            execution.error = {
                "message": str(handler_error),
                "type": type(handler_error).__name__,
            }
            execution.completed_at = datetime.now(timezone.utc)

            action.status = ActionRequestStatus.failed
            transitions.append(
                {
                    "from": "executing",
                    "to": "failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": str(handler_error),
                }
            )
            action.state_transitions = transitions

            db.commit()

            _record_outcome(
                db, action, execution, "failure", {"error": str(handler_error)}
            )

            return {"status": "failed", "error": str(handler_error)}

    except Exception as e:
        db.rollback()
        logger.error("dispatch_action failed: %s", e)
        raise self.retry(exc=e, countdown=30)
    finally:
        db.close()


def _record_outcome(
    db: SessionLocal,
    action: object,
    execution: object,
    outcome_type: str,
    result: dict,
) -> None:
    """Record action outcome and create feedback signal."""
    try:
        from ..models.action_outcome import ActionOutcome, OutcomeType
        from ..services.intelligence.signal_service import SignalService
        from ..models.signal import SignalSourceType, SignalType

        action_type_val = (
            action.action_type.value
            if hasattr(action.action_type, "value")
            else str(action.action_type)
        )

        outcome = ActionOutcome(
            action_request_id=action.id,
            execution_id=execution.id,
            outcome_type=OutcomeType(outcome_type),
            impact=result.get("result", {}),
            notes=f"Action {action_type_val} {outcome_type}",
        )
        db.add(outcome)
        db.flush()

        # Create feedback signal
        signal_svc = SignalService(db)
        signal = signal_svc.create_signal(
            project_id=action.project_id,
            user_id=action.user_id,
            source_type=SignalSourceType.action_outcome,
            signal_type=(
                SignalType.data_extracted
                if outcome_type == "success"
                else SignalType.user_flagged
            ),
            title=f"Action outcome: {action.title} ({outcome_type})",
            content=(
                f"Action type: {action_type_val}. Result: {outcome_type}"
            ),
            structured_data=result.get("result", {}),
            source_id=action.id,
            entity_id=action.entity_id,
        )
        outcome.feedback_signal_id = signal.id

        # Update recommendation status if action came from recommendation
        if action.recommendation_id and outcome_type == "success":
            from ..models.recommendation import Recommendation, RecommendationStatus

            rec = (
                db.query(Recommendation)
                .filter_by(id=action.recommendation_id)
                .first()
            )
            if rec:
                rec.status = RecommendationStatus.acted_on

        # Boost entity confidence on success
        if action.entity_id and outcome_type == "success":
            from ..models.entity import Entity

            entity = db.query(Entity).filter_by(id=action.entity_id).first()
            if entity and entity.confidence_score is not None:
                entity.confidence_score = min(
                    1.0, entity.confidence_score + 0.05
                )

        db.commit()
    except Exception as e:
        logger.error("Failed to record outcome for action %s: %s", action.id, e)
        try:
            db.rollback()
        except Exception:
            pass
