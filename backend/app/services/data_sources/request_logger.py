"""Log every data source request for cost/usage tracking."""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from ...models.source_request_log import SourceRequestLog

logger = logging.getLogger(__name__)


async def log_source_request(
    db: Session | None,
    data_source_id: uuid.UUID | None,
    request_type: str,
    request_params: dict[str, Any],
    response_status: int | None = None,
    response_preview: str | None = None,
    duration_ms: int | None = None,
    cost_usd: float | None = None,
    error: str | None = None,
    mission_id: uuid.UUID | None = None,
    crew_task_id: uuid.UUID | None = None,
) -> None:
    if not db or not data_source_id:
        return
    try:
        log = SourceRequestLog(
            data_source_id=data_source_id,
            mission_id=mission_id,
            crew_task_id=crew_task_id,
            request_type=request_type,
            request_params=request_params,
            response_status=response_status,
            response_preview=response_preview[:500] if response_preview else None,
            duration_ms=duration_ms,
            cost_usd=cost_usd,
            error=error,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.warning("Failed to log source request: %s", e)
        db.rollback()
