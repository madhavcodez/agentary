"""Thin async DocuSign eSignature client with an offline mock mode.

The client degrades gracefully when credentials are missing: every
public method returns deterministic mock values prefixed with
``mock-`` and logs a clear warning. No network call is made unless all
four credentials (integration key, user id, account id, RSA private
key) are configured AND the caller explicitly opts in via ``force``.

References (for future real-wire implementation):
* DocuSign JWT grant: https://developers.docusign.com/platform/auth/jwt/
* Envelope create API: https://developers.docusign.com/docs/esign-rest-api/
"""
from __future__ import annotations

import base64
import logging
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Final

import httpx
from jose import jwt

from ...config import settings
from .dto import ContractDraft

logger = logging.getLogger(__name__)

_DOCUSIGN_BASE_URLS: Final[dict[str, str]] = {
    "demo": "https://demo.docusign.net/restapi/v2.1",
    "prod": "https://www.docusign.net/restapi/v2.1",
    "production": "https://www.docusign.net/restapi/v2.1",
}
_DOCUSIGN_AUTH_HOSTS: Final[dict[str, str]] = {
    "demo": "account-d.docusign.com",
    "prod": "account.docusign.com",
    "production": "account.docusign.com",
}
_JWT_SCOPES: Final[str] = "signature impersonation"
_JWT_TTL_SECONDS: Final[int] = 3600


class EnvelopeStatus(str, Enum):
    """Subset of DocuSign envelope statuses we care about."""

    CREATED = "created"
    SENT = "sent"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    DECLINED = "declined"
    VOIDED = "voided"
    MOCK = "mock"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Signer:
    """One signer on a DocuSign envelope."""

    email: str
    name: str
    role: str
    routing_order: int = 1


@dataclass(frozen=True)
class EnvelopeId:
    """Opaque identifier for a created envelope."""

    value: str
    is_mock: bool


def _has_credentials() -> bool:
    """Check whether all four required DocuSign settings are populated."""
    return bool(
        settings.docusign_integration_key
        and settings.docusign_user_id
        and settings.docusign_account_id
        and settings.docusign_rsa_private_key_b64
    )


def _base_url() -> str:
    env = (settings.docusign_environment or "demo").lower()
    return _DOCUSIGN_BASE_URLS.get(env, _DOCUSIGN_BASE_URLS["demo"])


def _auth_host() -> str:
    env = (settings.docusign_environment or "demo").lower()
    return _DOCUSIGN_AUTH_HOSTS.get(env, _DOCUSIGN_AUTH_HOSTS["demo"])


def _build_jwt_assertion() -> str:
    """Build a JWT assertion to exchange for a DocuSign access token.

    Audit fixes (security #11 / code-review #10): wrap the entire body
    in a single try/except so:
      * ``binascii.Error`` from malformed base64 does not surface as a
        500 traceback
      * raw RSA key bytes or PEM fragments never appear in the bubbled
        up error — we log the original exception server-side with
        ``logger.exception`` but raise a sanitised ``RuntimeError``.
    """
    try:
        private_key = base64.b64decode(
            settings.docusign_rsa_private_key_b64
        ).decode("utf-8")
        now = int(time.time())
        payload = {
            "iss": settings.docusign_integration_key,
            "sub": settings.docusign_user_id,
            "aud": _auth_host(),
            "iat": now,
            "exp": now + _JWT_TTL_SECONDS,
            "scope": _JWT_SCOPES,
        }
        return jwt.encode(payload, private_key, algorithm="RS256")
    except Exception:  # noqa: BLE001 — intentional broad catch + sanitisation
        logger.exception("DocuSign JWT build failed")
        raise RuntimeError("DocuSign JWT build failed") from None


async def _fetch_access_token(client: httpx.AsyncClient) -> str:
    """Exchange a signed JWT for a short-lived DocuSign access token."""
    assertion = _build_jwt_assertion()
    resp = await client.post(
        f"https://{_auth_host()}/oauth/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=20.0,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("DocuSign auth succeeded but returned no access_token")
    return str(token)


def _build_envelope_payload(
    contract: ContractDraft, signers: list[Signer]
) -> dict[str, object]:
    """Shape the payload required by ``POST /accounts/{id}/envelopes``."""
    document_b64 = base64.b64encode(contract.pdf_bytes).decode("ascii")
    return {
        "emailSubject": f"Please sign: {contract.metadata.get('document_title', 'Pool Installation Agreement')}",
        "documents": [
            {
                "documentBase64": document_b64,
                "name": "PoolInstallationAgreement.pdf",
                "fileExtension": "pdf",
                "documentId": "1",
            }
        ],
        "recipients": {
            "signers": [
                {
                    "email": s.email,
                    "name": s.name,
                    "roleName": s.role,
                    "recipientId": str(i + 1),
                    "routingOrder": str(s.routing_order),
                }
                for i, s in enumerate(signers)
            ]
        },
        "status": "sent",
    }


async def create_envelope(
    contract: ContractDraft,
    signers: list[Signer],
    force: bool = False,
) -> EnvelopeId:
    """Create a DocuSign envelope, or a mock envelope if unsafe.

    A real envelope is only created when **all** of the following are
    true:

    * ``force=True`` (caller explicitly opted in)
    * All four DocuSign credentials are configured
    * ``contract.attorney_review_status == "APPROVED"``

    Otherwise we return a ``mock-`` envelope ID and log the reason.
    """
    if not signers:
        raise ValueError("Cannot create envelope with zero signers")

    if contract.attorney_review_status != "APPROVED":
        logger.warning(
            "DocuSign envelope NOT created: attorney_review_status=%s for draft %s",
            contract.attorney_review_status,
            contract.draft_id,
        )
        return EnvelopeId(value=f"mock-pending-review-{uuid.uuid4()}", is_mock=True)

    if not force:
        logger.warning(
            "DocuSign envelope NOT created: force=False for draft %s",
            contract.draft_id,
        )
        return EnvelopeId(value=f"mock-force-false-{uuid.uuid4()}", is_mock=True)

    if not _has_credentials():
        logger.warning(
            "DocuSign credentials missing; returning mock envelope for draft %s",
            contract.draft_id,
        )
        return EnvelopeId(value=f"mock-no-creds-{uuid.uuid4()}", is_mock=True)

    payload = _build_envelope_payload(contract, signers)
    async with httpx.AsyncClient() as client:
        token = await _fetch_access_token(client)
        url = f"{_base_url()}/accounts/{settings.docusign_account_id}/envelopes"
        resp = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        envelope_id = str(resp.json().get("envelopeId") or "")
        if not envelope_id:
            raise RuntimeError("DocuSign returned no envelopeId")
        logger.info("Created DocuSign envelope %s for draft %s", envelope_id, contract.draft_id)
        return EnvelopeId(value=envelope_id, is_mock=False)


async def get_envelope_status(envelope_id: str) -> EnvelopeStatus:
    """Return the current status of a DocuSign envelope.

    Mock envelope IDs (``mock-*``) always resolve to ``EnvelopeStatus.MOCK``
    without any network call.
    """
    if envelope_id.startswith("mock-"):
        return EnvelopeStatus.MOCK

    if not _has_credentials():
        logger.warning(
            "DocuSign credentials missing; cannot fetch status for %s", envelope_id
        )
        return EnvelopeStatus.UNKNOWN

    async with httpx.AsyncClient() as client:
        token = await _fetch_access_token(client)
        url = (
            f"{_base_url()}/accounts/{settings.docusign_account_id}"
            f"/envelopes/{envelope_id}"
        )
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        )
        resp.raise_for_status()
        raw = str(resp.json().get("status") or "unknown").lower()
        try:
            return EnvelopeStatus(raw)
        except ValueError:
            return EnvelopeStatus.UNKNOWN
