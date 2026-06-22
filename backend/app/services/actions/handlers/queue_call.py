"""Queue a voice extraction call."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest
from ....models.voice_extraction import CallRecord, CallStatus

logger = logging.getLogger(__name__)


class QueueCallHandler:
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        params = action.parameters or {}
        session_id = params.get("voice_session_id")
        phone = params.get("phone_number")
        target_name = params.get("target_name")

        if not session_id:
            return {
                "result": {"error": "Missing voice_session_id"},
                "side_effects": [],
            }

        call = CallRecord(
            voice_extraction_id=session_id,
            project_id=action.project_id,
            phone_number=phone or "",
            target_name=target_name or "Unknown",
            status=CallStatus.pending,
        )
        db.add(call)
        db.flush()

        return {
            "result": {
                "call_id": str(call.id),
                "phone": phone,
                "target": target_name,
            },
            "side_effects": [{"type": "call_queued", "call_id": str(call.id)}],
        }
