"""Webhook signature verification for inbound provider callbacks.

Provider webhooks must be authenticated. Without these checks, anyone with the
public webhook URL can forge call statuses, inject transcripts, or manipulate
suppression lists. The verifiers here cover the providers Agentary calls back:

- Twilio uses HMAC-SHA1 over the public URL + sorted form parameters, signed
  with the account ``Auth Token`` and delivered in the ``X-Twilio-Signature``
  header. See https://www.twilio.com/docs/usage/webhooks/webhooks-security.
- Resend uses Svix-style HMAC-SHA256 over ``{id}.{timestamp}.{payload}`` with
  the webhook secret, delivered as ``v1,<base64>`` in ``svix-signature`` (or
  ``Webhook-Signature``). See https://resend.com/docs/dashboard/webhooks/verify.

The functions are framework-agnostic — they raise ``WebhookVerificationError``
on failure and return ``None`` on success — so they can be reused from FastAPI
dependencies, Celery tasks, or one-off scripts.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from collections.abc import Mapping

from fastapi import HTTPException, Request, status

from ..config import settings

logger = logging.getLogger(__name__)


class WebhookVerificationError(Exception):
    """Raised when a webhook signature fails verification."""


# Tolerance window for replay protection. Five minutes is the Svix default
# and aligns with Twilio's own clock-skew guidance.
_REPLAY_TOLERANCE_SECONDS = 5 * 60


# ── Twilio ────────────────────────────────────────────────────────────


def _twilio_expected_signature(auth_token: str, url: str, form: Mapping[str, str]) -> str:
    """Compute the expected ``X-Twilio-Signature`` value.

    Twilio concatenates the full URL with the form parameters in *sorted key*
    order (key + value, no separators) and signs the result with HMAC-SHA1.
    The signature is base64-encoded.
    """
    data = url + "".join(f"{key}{form[key]}" for key in sorted(form))
    digest = hmac.new(auth_token.encode("utf-8"), data.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("ascii")


def _twilio_full_url(request: Request) -> str:
    """Reconstruct the public URL Twilio used when posting the webhook.

    Twilio signs the URL it called. Behind a proxy, ``request.url`` reflects
    the internal hostname, not the public one. Operators must set
    ``TWILIO_WEBHOOK_BASE_URL`` to the public origin (e.g.
    ``https://api.example.com``); we then append the request path + query.
    """
    base = settings.twilio_webhook_base_url.rstrip("/")
    if not base:
        # Fall back to whatever FastAPI sees; safe only when no proxy is in
        # front of the app.
        return str(request.url)
    path = request.url.path
    query = request.url.query
    return f"{base}{path}?{query}" if query else f"{base}{path}"


async def verify_twilio_signature(request: Request) -> Mapping[str, str]:
    """Validate ``X-Twilio-Signature`` and return the parsed form body.

    Raises ``HTTPException(403)`` if the header is missing or the signature
    does not match. Returns the form as a ``dict[str, str]`` so callers don't
    have to re-parse the body.
    """
    auth_token = settings.twilio_auth_token
    if not auth_token:
        logger.error("Twilio webhook hit with no TWILIO_AUTH_TOKEN configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook verification not configured",
        )

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Twilio-Signature header",
        )

    # FastAPI's ``request.form()`` returns a multi-dict; coerce to plain str→str
    # because Twilio's signature ignores file uploads (we have none) and only
    # mixes string values.
    form = await request.form()
    form_dict: dict[str, str] = {k: str(v) for k, v in form.items()}

    url = _twilio_full_url(request)
    expected = _twilio_expected_signature(auth_token, url, form_dict)

    if not hmac.compare_digest(expected, signature):
        # Don't echo the expected/received pair into the response — that helps
        # an attacker iterate. Log the URL only at INFO; the signatures stay
        # in operator-only logs.
        logger.warning("Twilio signature mismatch for url=%s", url)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature",
        )

    return form_dict


# ── Resend ────────────────────────────────────────────────────────────


def _parse_svix_signature_header(header: str) -> list[str]:
    """Extract the v1 signatures from a Svix-formatted header.

    The header looks like ``v1,abc... v1,def...`` (space-separated). Only the
    ``v1`` versions are accepted; future schemes will be added explicitly.
    """
    sigs: list[str] = []
    for entry in header.split():
        scheme, _, value = entry.partition(",")
        if scheme == "v1" and value:
            sigs.append(value)
    return sigs


def verify_resend_signature(
    body: bytes,
    headers: Mapping[str, str],
    secret: str | None = None,
) -> None:
    """Validate Svix headers on a Resend webhook.

    The signed payload is ``{webhook_id}.{timestamp}.{body}``. The secret may
    be supplied raw or with the ``whsec_`` prefix Resend hands out.

    Raises ``HTTPException`` on any failure; returns ``None`` on success.
    """
    secret = secret if secret is not None else settings.resend_webhook_secret
    if not secret:
        logger.error("Resend webhook hit with no RESEND_WEBHOOK_SECRET configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook verification not configured",
        )

    # Resend's Svix integration sets these three. We check both casings —
    # different proxies normalize differently.
    def _header(name: str) -> str:
        return headers.get(name) or headers.get(name.lower()) or ""

    webhook_id = _header("svix-id") or _header("webhook-id")
    timestamp = _header("svix-timestamp") or _header("webhook-timestamp")
    signature_header = _header("svix-signature") or _header("webhook-signature")

    if not (webhook_id and timestamp and signature_header):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing webhook signature headers",
        )

    # Replay protection — reject anything outside a 5-minute window
    try:
        ts = int(timestamp)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Malformed webhook timestamp",
        ) from exc

    now = int(time.time())
    if abs(now - ts) > _REPLAY_TOLERANCE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook timestamp outside tolerance",
        )

    # Strip the optional whsec_ prefix and base64-decode the secret bytes
    raw_secret = secret
    if raw_secret.startswith("whsec_"):
        raw_secret = raw_secret[len("whsec_") :]
    try:
        secret_bytes = base64.b64decode(raw_secret)
    except (ValueError, base64.binascii.Error):
        # Fall back to treating the secret as a plain UTF-8 string.
        secret_bytes = raw_secret.encode("utf-8")

    signed_payload = f"{webhook_id}.{timestamp}.".encode() + body
    expected = base64.b64encode(
        hmac.new(secret_bytes, signed_payload, hashlib.sha256).digest()
    ).decode("ascii")

    presented = _parse_svix_signature_header(signature_header)
    if not any(hmac.compare_digest(expected, sig) for sig in presented):
        logger.warning("Resend signature mismatch (webhook_id=%s)", webhook_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature",
        )
