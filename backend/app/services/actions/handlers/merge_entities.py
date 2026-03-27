"""Execute entity merge."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ....models.action_request import ActionRequest

logger = logging.getLogger(__name__)


class MergeEntitiesHandler:
    async def execute(self, action: ActionRequest, db: Session) -> dict:
        params = action.parameters or {}
        primary_id = params.get("primary_entity_id")
        secondary_id = params.get("secondary_entity_id")

        if not primary_id or not secondary_id:
            return {
                "result": {
                    "error": "Missing primary_entity_id or secondary_entity_id"
                },
                "side_effects": [],
            }

        try:
            from ....services.entities.entity_service import EntityService

            svc = EntityService(db)
            result = await svc.merge_entities_enhanced(
                primary_id, secondary_id, action.user_id, action.project_id, db
            )
            return {
                "result": {
                    "merge_id": result.get("merge_id", ""),
                    "primary": primary_id,
                    "merged": secondary_id,
                },
                "side_effects": [
                    {
                        "type": "entities_merged",
                        "primary": primary_id,
                        "secondary": secondary_id,
                    }
                ],
            }
        except Exception as e:
            return {"result": {"error": str(e)}, "side_effects": []}
