"""Escalate -- create high-priority alert."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest
from ....models.alert import AlertRecord, AlertSeverityLevel, AlertType

logger = logging.getLogger(__name__)


class EscalateHandler:
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        params = action.parameters or {}
        alert = AlertRecord(
            monitor_id=params.get("monitor_id"),
            project_id=action.project_id,
            user_id=action.user_id,
            alert_type=AlertType.error,
            title=f"ESCALATION: {action.title}",
            message=params.get(
                "reason", action.description or "Escalated action requiring attention"
            ),
            severity=AlertSeverityLevel.critical,
            data={
                "action_request_id": str(action.id),
                "entity_id": str(action.entity_id) if action.entity_id else None,
            },
        )
        db.add(alert)
        db.flush()

        return {
            "result": {"alert_id": str(alert.id), "severity": "critical"},
            "side_effects": [{"type": "escalation_alert_created", "alert_id": str(alert.id)}],
        }
