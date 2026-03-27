"""Correlation ID middleware -- propagates a unique ID through each request."""

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Return the current request's correlation ID (empty string outside a request)."""
    return correlation_id_var.get()


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Reads or generates X-Correlation-ID and stores it in a context variable."""

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        correlation_id_var.set(cid)
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response
