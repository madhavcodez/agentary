"""Unit tests for the bounded retry handler with exponential backoff."""

import pytest

from app.models.enums import FailureCategory
from app.services.retry_handler import PermanentError, RetryableError, with_retry


class TestSuccessPath:
    """Tests for successful execution paths."""

    @pytest.mark.asyncio
    async def test_succeeds_first_try(self) -> None:
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await with_retry(func, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_returns_value_from_func(self) -> None:
        async def func():
            return {"data": [1, 2, 3]}

        result = await with_retry(func, max_retries=1, base_delay=0.01)
        assert result == {"data": [1, 2, 3]}


class TestRetryBehavior:
    """Tests for retry logic on transient errors."""

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self) -> None:
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError(
                    "transient", FailureCategory.transient_connector
                )
            return "success"

        result = await with_retry(func, max_retries=3, base_delay=0.01)
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retries_on_model_error(self) -> None:
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RetryableError("model err", FailureCategory.model_error)
            return "ok"

        result = await with_retry(func, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_rate_limited(self) -> None:
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RetryableError(
                    "rate limited", FailureCategory.rate_limited, retry_after=0.01
                )
            return "ok"

        result = await with_retry(func, max_retries=2, base_delay=0.01)
        assert result == "ok"
        assert call_count == 2


class TestPermanentErrors:
    """Tests for permanent error handling."""

    @pytest.mark.asyncio
    async def test_raises_permanent_error_immediately(self) -> None:
        async def func():
            raise PermanentError("bad input", FailureCategory.validation)

        with pytest.raises(PermanentError):
            await with_retry(func, max_retries=3, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_permanent_error_preserves_category(self) -> None:
        async def func():
            raise PermanentError("bad input", FailureCategory.validation)

        with pytest.raises(PermanentError) as exc_info:
            await with_retry(func, max_retries=3, base_delay=0.01)
        assert exc_info.value.category == FailureCategory.validation

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self) -> None:
        async def func():
            raise RetryableError(
                "always fails", FailureCategory.transient_connector
            )

        with pytest.raises(PermanentError):
            await with_retry(func, max_retries=2, base_delay=0.01)

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_preserves_category(self) -> None:
        async def func():
            raise RetryableError(
                "always fails", FailureCategory.transient_connector
            )

        with pytest.raises(PermanentError) as exc_info:
            await with_retry(func, max_retries=2, base_delay=0.01)
        assert exc_info.value.category == FailureCategory.transient_connector

    @pytest.mark.asyncio
    async def test_unexpected_error_becomes_permanent(self) -> None:
        async def func():
            raise ValueError("unexpected")

        with pytest.raises(PermanentError) as exc_info:
            await with_retry(func, max_retries=1, base_delay=0.01)
        assert exc_info.value.category == FailureCategory.internal


class TestNonRetryableCategories:
    """Tests for errors whose category is not in the retryable set."""

    @pytest.mark.asyncio
    async def test_validation_category_not_retried(self) -> None:
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            raise RetryableError("bad data", FailureCategory.validation)

        with pytest.raises(PermanentError):
            await with_retry(func, max_retries=3, base_delay=0.01)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_timeout_category_not_retried_by_default(self) -> None:
        call_count = 0

        async def func():
            nonlocal call_count
            call_count += 1
            raise RetryableError("timed out", FailureCategory.timeout)

        with pytest.raises(PermanentError):
            await with_retry(func, max_retries=3, base_delay=0.01)
        assert call_count == 1


class TestRetryableErrorAttributes:
    """Tests for RetryableError exception attributes."""

    def test_retryable_error_has_category(self) -> None:
        err = RetryableError("test", FailureCategory.transient_connector)
        assert err.category == FailureCategory.transient_connector

    def test_retryable_error_has_retry_after(self) -> None:
        err = RetryableError(
            "test", FailureCategory.rate_limited, retry_after=5.0
        )
        assert err.retry_after == 5.0

    def test_retryable_error_default_retry_after(self) -> None:
        err = RetryableError("test", FailureCategory.model_error)
        assert err.retry_after == 1.0


class TestPermanentErrorAttributes:
    """Tests for PermanentError exception attributes."""

    def test_permanent_error_has_category(self) -> None:
        err = PermanentError("test", FailureCategory.internal)
        assert err.category == FailureCategory.internal

    def test_permanent_error_message(self) -> None:
        err = PermanentError("something broke", FailureCategory.internal)
        assert str(err) == "something broke"
