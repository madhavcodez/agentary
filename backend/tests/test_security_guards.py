"""Tests for Phase 1 security primitives.

Coverage targets:
- ``python_executor`` rejects the bypasses that defeated the old blocklist
- ``url_guard`` blocks SSRF target ranges and revalidates redirects
- ``phone_guard`` enforces region / type / premium-prefix policy
- ``webhook_security`` validates Twilio and Resend signatures

These run without database or network access. They use ``pytest`` plain
markers — no fixtures required.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import time
from typing import Any

import pytest


# ── python_executor ───────────────────────────────────────────────────


@pytest.mark.unit
def test_python_executor_runs_safe_code() -> None:
    from app.services.crews.tools.python_executor import execute

    result = asyncio.run(execute("print(2 + 3)"))
    assert result["status"] == "success", result
    assert "5" in result["stdout"]


@pytest.mark.unit
def test_python_executor_blocks_os_import_via_split_string() -> None:
    """The old substring blocklist was bypassed by __import__('o'+'s').

    RestrictedPython rejects ``__import__`` entirely at compile time.
    """
    from app.services.crews.tools.python_executor import execute

    code = "m = __import__('o' + 's'); print(m.getcwd())"
    result = asyncio.run(execute(code))
    assert result["status"] == "error", result


@pytest.mark.unit
def test_python_executor_blocks_importlib() -> None:
    from app.services.crews.tools.python_executor import execute

    code = "import importlib; importlib.import_module('subprocess')"
    result = asyncio.run(execute(code))
    assert result["status"] == "error", result


@pytest.mark.unit
def test_python_executor_blocks_open() -> None:
    from app.services.crews.tools.python_executor import execute

    code = "print(open('/etc/passwd').read())"
    result = asyncio.run(execute(code))
    assert result["status"] == "error", result


@pytest.mark.unit
def test_python_executor_blocks_exec() -> None:
    from app.services.crews.tools.python_executor import execute

    code = "exec('print(1)')"
    result = asyncio.run(execute(code))
    assert result["status"] == "error", result


@pytest.mark.unit
def test_python_executor_blocks_dunder_access() -> None:
    from app.services.crews.tools.python_executor import execute

    code = "print(().__class__.__bases__[0].__subclasses__())"
    result = asyncio.run(execute(code))
    assert result["status"] == "error", result


@pytest.mark.unit
def test_python_executor_allows_safe_stdlib_math() -> None:
    from app.services.crews.tools.python_executor import execute

    code = "import math; print(math.sqrt(16))"
    # Note: ``import`` is rejected even for whitelisted modules; the modules
    # are bound by *name* in the restricted globals. So callers don't write
    # imports.
    result = asyncio.run(execute(code))
    assert result["status"] == "error"

    code2 = "print(math.sqrt(16))"  # math is pre-bound
    result2 = asyncio.run(execute(code2))
    assert result2["status"] == "success"
    assert "4.0" in result2["stdout"]


# ── url_guard / SSRF ──────────────────────────────────────────────────


@pytest.mark.unit
def test_url_guard_blocks_loopback() -> None:
    from app.core.url_guard import UnsafeURLError, assert_safe_url

    with pytest.raises(UnsafeURLError):
        assert_safe_url("http://127.0.0.1/")


@pytest.mark.unit
def test_url_guard_blocks_imds() -> None:
    from app.core.url_guard import UnsafeURLError, assert_safe_url

    with pytest.raises(UnsafeURLError):
        assert_safe_url(
            "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
        )


@pytest.mark.unit
def test_url_guard_blocks_rfc1918() -> None:
    from app.core.url_guard import UnsafeURLError, assert_safe_url

    for ip in ("10.0.0.1", "192.168.1.1", "172.16.0.1"):
        with pytest.raises(UnsafeURLError):
            assert_safe_url(f"http://{ip}/")


@pytest.mark.unit
def test_url_guard_blocks_ipv6_loopback() -> None:
    from app.core.url_guard import UnsafeURLError, assert_safe_url

    with pytest.raises(UnsafeURLError):
        assert_safe_url("http://[::1]/")


@pytest.mark.unit
def test_url_guard_rejects_file_scheme() -> None:
    from app.core.url_guard import UnsafeURLError, assert_safe_url

    with pytest.raises(UnsafeURLError):
        assert_safe_url("file:///etc/passwd")


@pytest.mark.unit
def test_url_guard_rejects_missing_host() -> None:
    from app.core.url_guard import UnsafeURLError, assert_safe_url

    with pytest.raises(UnsafeURLError):
        assert_safe_url("http://")


# ── phone_guard ────────────────────────────────────────────────────────


@pytest.mark.unit
def test_phone_guard_accepts_us_mobile() -> None:
    from app.core.phone_guard import validate_outbound_number

    # 415 area code is San Francisco; the specific test number is valid E.164
    assert validate_outbound_number("+14155551234").startswith("+1")


@pytest.mark.unit
def test_phone_guard_rejects_premium_900() -> None:
    from app.core.phone_guard import PhoneNumberRejected, validate_outbound_number

    with pytest.raises(PhoneNumberRejected):
        validate_outbound_number("+19005551234")


@pytest.mark.unit
def test_phone_guard_rejects_emergency_911() -> None:
    from app.core.phone_guard import PhoneNumberRejected, validate_outbound_number

    with pytest.raises(PhoneNumberRejected):
        validate_outbound_number("911")


@pytest.mark.unit
def test_phone_guard_rejects_foreign_region() -> None:
    from app.core.phone_guard import PhoneNumberRejected, validate_outbound_number

    # UK number — outside default US/CA allowlist
    with pytest.raises(PhoneNumberRejected):
        validate_outbound_number("+442012345678")


@pytest.mark.unit
def test_phone_guard_rejects_empty_input() -> None:
    from app.core.phone_guard import PhoneNumberRejected, validate_outbound_number

    with pytest.raises(PhoneNumberRejected):
        validate_outbound_number("")


# ── webhook_security ──────────────────────────────────────────────────


def _twilio_signature(token: str, url: str, params: dict[str, str]) -> str:
    data = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    digest = hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


@pytest.mark.unit
def test_twilio_signature_helper_matches_reference() -> None:
    from app.core.webhook_security import _twilio_expected_signature

    token = "test-token"
    url = "https://example.com/webhooks/twilio/voice-status"
    params = {"CallSid": "CA123", "CallStatus": "completed"}
    expected = _twilio_signature(token, url, params)
    assert _twilio_expected_signature(token, url, params) == expected


@pytest.mark.unit
def test_resend_signature_verifies(monkeypatch: Any) -> None:
    from app.core import webhook_security

    secret = "whsec_" + base64.b64encode(b"my-test-secret").decode()
    monkeypatch.setattr(
        webhook_security.settings, "resend_webhook_secret", secret, raising=False
    )

    body = b'{"type":"email.delivered","data":{}}'
    webhook_id = "msg_test_1"
    timestamp = str(int(time.time()))

    signed = f"{webhook_id}.{timestamp}.".encode() + body
    sig = base64.b64encode(
        hmac.new(b"my-test-secret", signed, hashlib.sha256).digest()
    ).decode()

    webhook_security.verify_resend_signature(
        body,
        {
            "svix-id": webhook_id,
            "svix-timestamp": timestamp,
            "svix-signature": f"v1,{sig}",
        },
    )


@pytest.mark.unit
def test_resend_signature_rejects_replay(monkeypatch: Any) -> None:
    from fastapi import HTTPException

    from app.core import webhook_security

    monkeypatch.setattr(
        webhook_security.settings, "resend_webhook_secret", "any-secret", raising=False
    )

    body = b"{}"
    old_timestamp = str(int(time.time()) - 60 * 60)  # 1 hour ago

    with pytest.raises(HTTPException) as exc:
        webhook_security.verify_resend_signature(
            body,
            {
                "svix-id": "msg_test_1",
                "svix-timestamp": old_timestamp,
                "svix-signature": "v1,xxx",
            },
        )
    assert exc.value.status_code == 403
