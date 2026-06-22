from __future__ import annotations

from datetime import UTC

from app.voice.policy.rules import OUTBOUND_LIMITS


class TestOutboundLimits:
    def test_max_daily_calls_defined(self):
        """Verify max_daily_calls is set to a reasonable limit."""
        assert "max_daily_calls" in OUTBOUND_LIMITS
        assert isinstance(OUTBOUND_LIMITS["max_daily_calls"], int)
        assert OUTBOUND_LIMITS["max_daily_calls"] == 20

    def test_min_company_cooldown_hours(self):
        """Verify the per-company cooldown period is defined."""
        assert "min_company_cooldown_hours" in OUTBOUND_LIMITS
        assert isinstance(OUTBOUND_LIMITS["min_company_cooldown_hours"], int)
        assert OUTBOUND_LIMITS["min_company_cooldown_hours"] == 48

    def test_max_attempts_per_contact(self):
        """Verify max retry attempts per contact."""
        assert "max_attempts_per_contact" in OUTBOUND_LIMITS
        assert isinstance(OUTBOUND_LIMITS["max_attempts_per_contact"], int)
        assert OUTBOUND_LIMITS["max_attempts_per_contact"] == 3


class TestRetryLogic:
    def test_should_retry_no_previous_log(self):
        """First attempt — should always retry."""
        from unittest.mock import MagicMock

        from app.services.campaign_orchestrator import _should_retry

        campaign = MagicMock()
        campaign.attempt_count = 0
        assert _should_retry(campaign, None) is True

    def test_should_not_retry_after_connected(self):
        """After a successful connection, no retry needed."""
        from unittest.mock import MagicMock

        from app.services.campaign_orchestrator import _should_retry

        campaign = MagicMock()
        campaign.attempt_count = 1

        last_log = MagicMock()
        last_log.outcome = "connected"
        last_log.created_at = None

        assert _should_retry(campaign, last_log) is False

    def test_should_retry_after_no_answer_past_backoff(self):
        """After a no-answer with backoff elapsed, should retry."""
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock

        from app.services.campaign_orchestrator import _should_retry

        campaign = MagicMock()
        campaign.attempt_count = 1

        last_log = MagicMock()
        last_log.outcome = "no_answer"
        last_log.created_at = datetime.now(UTC) - timedelta(hours=3)

        assert _should_retry(campaign, last_log) is True

    def test_should_not_retry_within_backoff(self):
        """Within the backoff window, should not retry."""
        from datetime import datetime, timedelta
        from unittest.mock import MagicMock

        from app.services.campaign_orchestrator import _should_retry

        campaign = MagicMock()
        campaign.attempt_count = 2  # 2nd attempt => backoff = 2h

        last_log = MagicMock()
        last_log.outcome = "no_answer"
        last_log.created_at = datetime.now(UTC) - timedelta(minutes=30)

        assert _should_retry(campaign, last_log) is False


class TestPolicyEngineOutbound:
    def test_business_hours_check(self):
        """Policy engine's pre-call check returns a valid structure."""
        from app.voice.policy.engine import PolicyEngine

        engine = PolicyEngine()
        result = engine.evaluate_pre_call({})
        assert "allowed" in result
        assert "violations" in result
        assert isinstance(result["violations"], list)

    def test_mid_call_check_clean_transcript(self):
        """Clean transcript passes mid-call policy check."""
        from app.voice.policy.engine import PolicyEngine

        engine = PolicyEngine()
        result = engine.evaluate_mid_call(
            "Hi, I am calling about the software engineer position."
        )
        assert result["allowed"] is True

    def test_mid_call_check_forbidden_topic(self):
        """Transcript mentioning forbidden topics fails policy check."""
        from app.voice.policy.engine import PolicyEngine

        engine = PolicyEngine()
        result = engine.evaluate_mid_call(
            "Let me share some competitor information with you."
        )
        assert result["allowed"] is False
        assert len(result["violations"]) > 0
