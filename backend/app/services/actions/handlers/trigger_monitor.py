"""Trigger a monitor check."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest

logger = logging.getLogger(__name__)


class TriggerMonitorHandler:
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        params = action.parameters or {}
        monitor_id = params.get("monitor_id")
        if not monitor_id:
            return {
                "result": {"error": "Missing monitor_id"},
                "side_effects": [],
            }

        try:
            from ....tasks.monitor_tasks import check_monitor

            check_monitor.delay(monitor_id)
            return {
                "result": {"monitor_id": monitor_id, "status": "check_queued"},
                "side_effects": [
                    {"type": "monitor_check_triggered", "monitor_id": monitor_id}
                ],
            }
        except Exception as e:
            return {"result": {"error": str(e)}, "side_effects": []}
