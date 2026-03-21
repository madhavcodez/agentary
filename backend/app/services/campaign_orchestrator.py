"""Legacy campaign orchestrator — stub for backward compatibility."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _should_retry(campaign, last_log) -> bool:
    """Determine if a campaign call should be retried."""
    if campaign.attempt_count == 0:
        return True

    if last_log is None:
        return True

    if getattr(last_log, "outcome", None) == "connected":
        return False

    max_attempts = campaign.max_attempts if isinstance(getattr(campaign, "max_attempts", None), int) else 3
    if campaign.attempt_count >= max_attempts:
        return False

    backoff_hours = 2 ** campaign.attempt_count
    if last_log.created_at:
        next_attempt = last_log.created_at + timedelta(hours=backoff_hours)
        if datetime.now(timezone.utc) < next_attempt:
            return False

    return True
