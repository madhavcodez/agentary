from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def tracked_operation(
    operation: str,
    **context: Any,
) -> AsyncGenerator[dict[str, Any]]:
    """Async context manager that logs start/end/duration/errors for any operation."""
    start_time = time.monotonic()
    metrics: dict[str, Any] = {"operation": operation, **context}

    await logger.ainfo(f"{operation}.started", **context)
    try:
        yield metrics
        duration = time.monotonic() - start_time
        metrics["duration_seconds"] = round(duration, 3)
        await logger.ainfo(f"{operation}.completed", duration=metrics["duration_seconds"], **context)
    except Exception as exc:
        duration = time.monotonic() - start_time
        metrics["duration_seconds"] = round(duration, 3)
        metrics["error"] = str(exc)
        await logger.aerror(f"{operation}.failed", error=str(exc), duration=metrics["duration_seconds"], **context)
        raise
