"""Trigger report generation."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest

logger = logging.getLogger(__name__)


class GenerateReportHandler:
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        params = action.parameters or {}
        report_id = params.get("report_id")
        if not report_id:
            return {
                "result": {"error": "Missing report_id"},
                "side_effects": [],
            }

        try:
            from ....tasks.report_tasks import generate_report

            generate_report.delay(report_id)
            return {
                "result": {"report_id": report_id, "status": "generation_queued"},
                "side_effects": [
                    {
                        "type": "report_generation_triggered",
                        "report_id": report_id,
                    }
                ],
            }
        except Exception as e:
            return {"result": {"error": str(e)}, "side_effects": []}
