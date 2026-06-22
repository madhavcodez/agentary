"""Bounded retry logic with exponential backoff for connector calls.

Provides RetryableError, PermanentError, and the with_retry helper
so that transient failures are retried and permanent ones propagate immediately.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from ..models.enums import FailureCategory

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Raised when an operation fails but may succeed on retry."""

    def __init__(
        self,
        message: str,
        category: FailureCategory,
        retry_after: float = 1.0,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.retry_after = retry_after


class PermanentError(Exception):
    """Raised when an operation fails and should not be retried."""

    def __init__(self, message: str, category: FailureCategory) -> None:
        super().__init__(message)
        self.category = category


async def with_retry(
    func: Callable[[], Awaitable[Any]],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_categories: tuple[FailureCategory, ...] = (
        FailureCategory.transient_connector,
        FailureCategory.model_error,
        FailureCategory.rate_limited,
    ),
) -> Any:
    """Execute *func* with exponential backoff retry for retryable errors.

    Args:
        func: An async callable (no arguments) to execute.
        max_retries: Maximum number of retry attempts after the initial call.
        base_delay: Starting delay in seconds between retries.
        max_delay: Maximum delay cap in seconds.
        retryable_categories: FailureCategory values eligible for retry.

    Returns:
        The return value of *func* on success.

    Raises:
        PermanentError: When retries are exhausted or the error is not retryable.
    """
    last_error: RetryableError | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except RetryableError as exc:
            last_error = exc
            if attempt < max_retries and exc.category in retryable_categories:
                delay = min(base_delay * (2**attempt), max_delay)
                if exc.retry_after:
                    delay = max(delay, exc.retry_after)
                logger.warning(
                    "Retryable error (attempt %d/%d, category=%s): %s — retrying in %.1fs",
                    attempt + 1,
                    max_retries + 1,
                    exc.category.value,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)
            else:
                raise PermanentError(str(exc), exc.category) from exc
        except PermanentError:
            raise
        except Exception as exc:
            raise PermanentError(str(exc), FailureCategory.internal) from exc

    raise PermanentError(
        str(last_error),
        last_error.category if last_error else FailureCategory.internal,
    )
