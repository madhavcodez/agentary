"""Create an internal task."""
from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest

logger = logging.getLogger(__name__)


class CreateTaskHandler:
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        params = action.parameters or {}
        # Store task info in action outcome -- actual Task model can be added later
        task_data = {
            "task_id": str(uuid.uuid4()),
            "title": params.get("task_title", action.title),
            "description": params.get("task_description", action.description),
            "assigned_to": params.get("assigned_to"),
            "due_date": params.get("due_date"),
            "priority": action.priority,
            "entity_id": str(action.entity_id) if action.entity_id else None,
            "project_id": str(action.project_id),
        }
        return {
            "result": task_data,
            "side_effects": [
                {"type": "task_created", "task_id": task_data["task_id"]}
            ],
        }
