"""Update entity/insight/recommendation status."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest
from ....models.entity import Entity
from ....models.insight import Insight
from ....models.recommendation import Recommendation

logger = logging.getLogger(__name__)


class UpdateStatusHandler:
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        params = action.parameters or {}
        target_type = params.get("target_type")  # entity, insight, recommendation
        target_id = params.get("target_id")
        new_status = params.get("new_status")

        if not all([target_type, target_id, new_status]):
            return {
                "result": {"error": "Missing target_type, target_id, or new_status"},
                "side_effects": [],
            }

        model_map = {
            "entity": Entity,
            "insight": Insight,
            "recommendation": Recommendation,
        }
        model = model_map.get(target_type)
        if not model:
            return {
                "result": {"error": f"Unknown target_type: {target_type}"},
                "side_effects": [],
            }

        obj = db.query(model).filter_by(id=target_id).first()
        if not obj:
            return {
                "result": {"error": f"{target_type} {target_id} not found"},
                "side_effects": [],
            }

        old_status = getattr(obj, "status", None) or getattr(obj, "is_active", None)

        if target_type == "insight":
            if new_status == "active":
                obj.is_active = True
            elif new_status == "inactive":
                obj.is_active = False
        elif hasattr(obj, "status"):
            obj.status = new_status

        db.flush()
        return {
            "result": {
                "target_type": target_type,
                "target_id": target_id,
                "old_status": str(old_status),
                "new_status": new_status,
            },
            "side_effects": [
                {
                    "type": "status_update",
                    "target": f"{target_type}:{target_id}",
                    "from": str(old_status),
                    "to": new_status,
                }
            ],
        }
