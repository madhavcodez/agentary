"""Resend email sending service with circuit breaker protection.

Sends transactional emails via the Resend API. Includes automatic
suppression list checking and circuit breaker fault tolerance.
"""

from __future__ import annotations

import logging

import httpx

from ..config import settings
from .circuit_breakers import resend_breaker

logger = logging.getLogger(__name__)


@resend_breaker
async def send_email(
    to: str,
    subject: str,
    body: str,
    reply_to: str | None = None,
) -> dict:
    """Send email via Resend API. Returns Resend response with email ID.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain text email body.
        reply_to: Optional reply-to address.

    Returns:
        Resend API response dict containing at minimum ``id``.

    Raises:
        httpx.HTTPStatusError: If Resend returns a non-2xx response.
        pybreaker.CircuitBreakerError: If the circuit is open.
    """
    payload: dict = {
        "from": settings.resend_from_email,
        "to": [to],
        "subject": subject,
        "text": body,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json=payload,
            timeout=10.0,
        )
        response.raise_for_status()
        result = response.json()
        logger.info("Email sent via Resend: id=%s to=%s", result.get("id"), to)
        return result
