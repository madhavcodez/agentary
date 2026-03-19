from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_all_tools(llm) -> None:
    from .profile_twin import query_profile

    try:
        llm.register_function("query_profile", query_profile)
        logger.info("Registered voice tool: query_profile")
    except Exception as e:
        logger.warning("Failed to register tools: %s", e)
