"""Circuit breaker pattern for external API resilience.

Wraps all external API calls (Gemini, Exa, Resend, Twilio, Qdrant)
with circuit breakers to prevent cascading failures. When an API
fails repeatedly, the circuit opens and fast-fails subsequent calls
until the reset timeout elapses.
"""

from __future__ import annotations

import logging

import pybreaker

logger = logging.getLogger(__name__)


class LoggingListener(pybreaker.CircuitBreakerListener):
    """Log all circuit breaker state transitions and failures."""

    def state_change(self, cb: pybreaker.CircuitBreaker, old_state: pybreaker.CircuitBreakerState, new_state: pybreaker.CircuitBreakerState) -> None:
        logger.warning(
            "Circuit breaker '%s' state: %s -> %s",
            cb.name, old_state.name, new_state.name,
        )

    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception) -> None:
        logger.error(
            "Circuit breaker '%s' recorded failure: %s", cb.name, exc,
        )


_listener = LoggingListener()

gemini_breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=60, name="gemini", listeners=[_listener],
)
exa_breaker = pybreaker.CircuitBreaker(
    fail_max=3, reset_timeout=120, name="exa", listeners=[_listener],
)
resend_breaker = pybreaker.CircuitBreaker(
    fail_max=3, reset_timeout=60, name="resend", listeners=[_listener],
)
twilio_breaker = pybreaker.CircuitBreaker(
    fail_max=3, reset_timeout=120, name="twilio", listeners=[_listener],
)
qdrant_breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=30, name="qdrant", listeners=[_listener],
)
google_places_breaker = pybreaker.CircuitBreaker(
    fail_max=3, reset_timeout=120, name="google_places", listeners=[_listener],
)
yelp_breaker = pybreaker.CircuitBreaker(
    fail_max=3, reset_timeout=120, name="yelp", listeners=[_listener],
)
crunchbase_breaker = pybreaker.CircuitBreaker(
    fail_max=3, reset_timeout=120, name="crunchbase", listeners=[_listener],
)
zillow_breaker = pybreaker.CircuitBreaker(
    fail_max=3, reset_timeout=120, name="zillow", listeners=[_listener],
)
web_scraper_breaker = pybreaker.CircuitBreaker(
    fail_max=5, reset_timeout=60, name="web_scraper", listeners=[_listener],
)


def get_breaker_status() -> dict:
    """Return current state of all circuit breakers for health checks."""
    breakers = [
        gemini_breaker,
        exa_breaker,
        resend_breaker,
        twilio_breaker,
        qdrant_breaker,
        google_places_breaker,
        yelp_breaker,
        crunchbase_breaker,
        zillow_breaker,
        web_scraper_breaker,
    ]
    return {
        b.name: {
            "state": b.current_state,
            "fail_count": b.fail_counter,
            "fail_max": b.fail_max,
            "reset_timeout": b.reset_timeout,
        }
        for b in breakers
    }
