from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def request_handoff(reason: str, caller_name: str | None = None) -> str:
    logger.info("Handoff requested: reason=%s, caller=%s", reason, caller_name)
    return f"Transfer request logged: {reason}. A human will follow up shortly."
