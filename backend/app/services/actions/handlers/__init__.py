"""Action handler registry."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest


class ActionHandler(Protocol):
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        """Execute the action. Returns {"result": ..., "side_effects": [...]}"""
        ...


# Registry maps action_type -> handler instance
_HANDLERS: dict[str, ActionHandler] = {}


def register_handler(action_type: str, handler: ActionHandler) -> None:
    _HANDLERS[action_type] = handler


def get_handler(action_type: str) -> ActionHandler | None:
    return _HANDLERS.get(action_type)


def register_all_handlers() -> None:
    """Register all built-in handlers."""
    from .create_task import CreateTaskHandler
    from .escalate import EscalateHandler
    from .generate_report import GenerateReportHandler
    from .merge_entities import MergeEntitiesHandler
    from .queue_call import QueueCallHandler
    from .send_alert import SendAlertHandler
    from .trigger_monitor import TriggerMonitorHandler
    from .trigger_workflow import TriggerWorkflowHandler
    from .update_status import UpdateStatusHandler

    register_handler("update_status", UpdateStatusHandler())
    register_handler("send_alert", SendAlertHandler())
    register_handler("trigger_workflow", TriggerWorkflowHandler())
    register_handler("trigger_monitor", TriggerMonitorHandler())
    register_handler("create_task", CreateTaskHandler())
    register_handler("generate_report", GenerateReportHandler())
    register_handler("queue_call", QueueCallHandler())
    register_handler("merge_entities", MergeEntitiesHandler())
    register_handler("escalate", EscalateHandler())
