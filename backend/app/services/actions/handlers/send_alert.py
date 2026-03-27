"""Send alert via dashboard."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest
from ....models.alert import AlertRecord, AlertSeverityLevel, AlertType

logger = logging.getLogger(__name__)


class SendAlertHandler:
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        params = action.parameters or {}

        # Map string severity to enum, default to medium
        severity_str = params.get("severity", "medium")
        try:
            severity = AlertSeverityLevel(severity_str)
        except ValueError:
            severity = AlertSeverityLevel.medium

        # Map alert_type string to enum, default to new_data
        alert_type_str = params.get("alert_type", "new_data")
        try:
            alert_type = AlertType(alert_type_str)
        except ValueError:
            alert_type = AlertType.new_data

        alert = AlertRecord(
            monitor_id=params.get("monitor_id"),
            project_id=action.project_id,
            user_id=action.user_id,
            alert_type=alert_type,
            title=params.get("alert_title", action.title),
            message=params.get("alert_message", action.description or action.title),
            severity=severity,
            data={
                "action_request_id": str(action.id),
                "source": "action_system",
            },
        )
        db.add(alert)
        db.flush()
        return {
            "result": {"alert_id": str(alert.id), "title": alert.title},
            "side_effects": [{"type": "alert_created", "alert_id": str(alert.id)}],
        }
