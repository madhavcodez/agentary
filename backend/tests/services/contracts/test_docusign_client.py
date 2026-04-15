"""Unit tests for the DocuSign client's offline / mock-mode behavior.

These tests never hit the DocuSign API. They assert:
* Missing credentials => mock envelope + warning.
* ``force=False`` => mock envelope regardless of credentials.
* ``PENDING-LEGAL`` review status => mock envelope regardless of force.
* ``get_envelope_status`` on a mock id short-circuits to MOCK.
"""
from __future__ import annotations

import hashlib

import pytest

from app.services.contracts.docusign_client import (
    EnvelopeStatus,
    Signer,
    create_envelope,
    get_envelope_status,
)
from app.services.contracts.dto import ContractDraft


def _draft(review_status: str = "PENDING-LEGAL") -> ContractDraft:
    body = b"%PDF-1.4\n% test\n"
    return ContractDraft(
        draft_id="draft-test-1",
        template_key="tx_pool_installation_v1",
        pdf_bytes=body,
        html="<html></html>",
        markdown="# test",
        metadata={"document_title": "Test Pool Agreement"},
        attorney_review_status=review_status,  # type: ignore[arg-type]
        sha256=hashlib.sha256(body).hexdigest(),
    )


def _signers() -> list[Signer]:
    return [Signer(email="buyer@example.com", name="Buyer One", role="Buyer")]


@pytest.mark.asyncio
async def test_create_envelope_returns_mock_when_review_pending(monkeypatch):
    # Even with force=True and creds, PENDING-LEGAL must short-circuit.
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_integration_key",
        "key",
    )
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_user_id", "user"
    )
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_account_id",
        "account",
    )
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_rsa_private_key_b64",
        "ZmFrZQ==",
    )

    env = await create_envelope(_draft("PENDING-LEGAL"), _signers(), force=True)
    assert env.is_mock is True
    assert env.value.startswith("mock-pending-review-")


@pytest.mark.asyncio
async def test_create_envelope_returns_mock_when_force_false(monkeypatch):
    env = await create_envelope(_draft("APPROVED"), _signers(), force=False)
    assert env.is_mock is True
    assert env.value.startswith("mock-force-false-")


@pytest.mark.asyncio
async def test_create_envelope_returns_mock_when_creds_missing(monkeypatch):
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_integration_key", ""
    )
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_user_id", ""
    )
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_account_id", ""
    )
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_rsa_private_key_b64",
        "",
    )

    env = await create_envelope(_draft("APPROVED"), _signers(), force=True)
    assert env.is_mock is True
    assert env.value.startswith("mock-no-creds-")


@pytest.mark.asyncio
async def test_create_envelope_raises_when_no_signers():
    with pytest.raises(ValueError):
        await create_envelope(_draft("APPROVED"), [], force=True)


@pytest.mark.asyncio
async def test_get_envelope_status_short_circuits_mock():
    status = await get_envelope_status("mock-no-creds-abc")
    assert status == EnvelopeStatus.MOCK


@pytest.mark.asyncio
async def test_get_envelope_status_unknown_without_creds(monkeypatch):
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_integration_key", ""
    )
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_user_id", ""
    )
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_account_id", ""
    )
    monkeypatch.setattr(
        "app.services.contracts.docusign_client.settings.docusign_rsa_private_key_b64",
        "",
    )
    status = await get_envelope_status("real-looking-id-abc123")
    assert status == EnvelopeStatus.UNKNOWN
