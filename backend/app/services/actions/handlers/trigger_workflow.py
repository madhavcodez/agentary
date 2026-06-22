"""Trigger a workflow run."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest
from ....models.enums import RunStatus
from ....models.workflow import Workflow
from ....models.workflow_run import WorkflowRun

logger = logging.getLogger(__name__)


class TriggerWorkflowHandler:
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        params = action.parameters or {}
        workflow_id = params.get("workflow_id")
        if not workflow_id:
            return {
                "result": {"error": "Missing workflow_id"},
                "side_effects": [],
            }

        workflow = db.query(Workflow).filter_by(id=workflow_id).first()
        if not workflow:
            return {
                "result": {"error": f"Workflow {workflow_id} not found"},
                "side_effects": [],
            }

        run = WorkflowRun(
            workflow_id=workflow.id,
            user_id=action.user_id,
            status=RunStatus.created,
            trigger_type="action",
        )
        db.add(run)
        db.flush()

        return {
            "result": {"workflow_id": str(workflow.id), "run_id": str(run.id)},
            "side_effects": [{"type": "workflow_run_created", "run_id": str(run.id)}],
        }
