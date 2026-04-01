"""Structured JSON logging for Agentary."""

import json
import logging
import sys
from datetime import datetime, timezone


class CorrelationFilter(logging.Filter):
    """Inject the current request's correlation ID into every log record.

    The correlation ID is read from the :data:`correlation_id_var` context
    variable that is set by :class:`CorrelationMiddleware`.  If no
    correlation ID is present (e.g. during startup or in background tasks)
    the attribute defaults to an empty string.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Lazy import to avoid circular dependency at module load time
        from .correlation import get_correlation_id

        record.correlation_id = get_correlation_id()  # type: ignore[attr-defined]
        return True


class JSONFormatter(logging.Formatter):
    """Emit every log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Correlation ID (injected by CorrelationFilter from contextvars)
        correlation_id = getattr(record, "correlation_id", None)
        if correlation_id:
            log_entry["correlation_id"] = str(correlation_id)

        # User ID when available
        user_id = getattr(record, "user_id", None)
        if user_id:
            log_entry["user_id"] = str(user_id)

        # Exception traceback
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with JSON output to stdout."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(CorrelationFilter())
    root.addHandler(handler)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
