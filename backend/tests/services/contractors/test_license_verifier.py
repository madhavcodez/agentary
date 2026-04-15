"""Unit tests for the TDLR license verifier."""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.contractors import license_verifier
from app.services.contractors.license_verifier import (
    LicenseStatus,
    _parse_tdlr_html,
    verify_license,
    verify_tx_license,
)


# ---------------------------------------------------------------------------
# HTML parser tests
# ---------------------------------------------------------------------------

_SAMPLE_HTML_MATCH = """
<html><body>
<h2>License Search Results</h2>
<table>
  <tr>
    <th>Business Name</th>
    <th>License Number</th>
    <th>License Type</th>
    <th>Status</th>
    <th>Expiration Date</th>
  </tr>
  <tr>
    <td>BlueWave Pools LLC</td>
    <td>APS123456</td>
    <td>Appliance Installer - Pool</td>
    <td>Active</td>
    <td>2027-05-31</td>
  </tr>
</table>
</body></html>
"""

_SAMPLE_HTML_NO_MATCH = """
<html><body>
<h2>License Search Results</h2>
<p>No records found for your search.</p>
</body></html>
"""


def test_parse_tdlr_html_extracts_match() -> None:
    status = _parse_tdlr_html(_SAMPLE_HTML_MATCH)
    assert status.found is True
    assert status.license_number == "APS123456"
    assert status.status == "Active"
    assert status.classification == "Appliance Installer - Pool"
    assert status.expires_at == "2027-05-31"


def test_parse_tdlr_html_no_records() -> None:
    status = _parse_tdlr_html(_SAMPLE_HTML_NO_MATCH)
    assert status.found is False
    assert status.status == "no_records"


def test_parse_tdlr_html_empty() -> None:
    status = _parse_tdlr_html("")
    assert status.found is False
    assert status.status == "empty_response"


def test_parse_tdlr_html_no_table() -> None:
    status = _parse_tdlr_html("<html><body>oops</body></html>")
    assert status.found is False
    assert status.status == "no_table"


# ---------------------------------------------------------------------------
# verify_tx_license with mocked httpx
# ---------------------------------------------------------------------------


def _mock_get_no_cache(*args: Any, **kwargs: Any) -> AsyncMock:
    mock = AsyncMock(return_value=None)
    return mock


@pytest.fixture(autouse=True)
def _bypass_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the verifier to skip Redis during every test."""

    async def _none() -> None:
        return None

    monkeypatch.setattr(license_verifier, "_get_redis", _none)


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "bad",
                request=httpx.Request("GET", "https://x"),
                response=httpx.Response(self.status_code),
            )


class _FakeClient:
    def __init__(self, response: _FakeResponse | Exception) -> None:
        self._response = response

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        return None

    async def get(self, url: str, params: Any = None) -> _FakeResponse:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


@pytest.mark.asyncio
async def test_verify_tx_license_found() -> None:
    with patch.object(
        httpx,
        "AsyncClient",
        return_value=_FakeClient(_FakeResponse(_SAMPLE_HTML_MATCH)),
    ):
        status = await verify_tx_license(
            business_name="BlueWave Pools LLC", city="Plano"
        )
    assert status.found is True
    assert status.license_number == "APS123456"


@pytest.mark.asyncio
async def test_verify_tx_license_no_records() -> None:
    with patch.object(
        httpx,
        "AsyncClient",
        return_value=_FakeClient(_FakeResponse(_SAMPLE_HTML_NO_MATCH)),
    ):
        status = await verify_tx_license(business_name="Ghost Pools")
    assert status.found is False
    assert status.status == "no_records"


@pytest.mark.asyncio
async def test_verify_tx_license_timeout_returns_not_found() -> None:
    with patch.object(
        httpx,
        "AsyncClient",
        return_value=_FakeClient(httpx.TimeoutException("slow")),
    ):
        status = await verify_tx_license(business_name="BlueWave")
    assert status.found is False
    assert status.status == "timeout"


@pytest.mark.asyncio
async def test_verify_tx_license_rejects_blank_name() -> None:
    status = await verify_tx_license(business_name="   ")
    assert status.found is False
    assert status.status == "no_business_name"


@pytest.mark.asyncio
async def test_verify_tx_license_handles_http_error() -> None:
    with patch.object(
        httpx,
        "AsyncClient",
        return_value=_FakeClient(_FakeResponse("", status_code=503)),
    ):
        status = await verify_tx_license(business_name="BlueWave")
    assert status.found is False
    assert status.status == "http_503"


# ---------------------------------------------------------------------------
# Dispatcher tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_license_routes_tx_to_tx_verifier() -> None:
    sentinel = LicenseStatus(found=True, license_number="ROUTED-OK")
    with patch.object(
        license_verifier, "verify_tx_license", AsyncMock(return_value=sentinel)
    ) as mock:
        result = await verify_license(
            state="TX", business_name="BlueWave", city="Plano"
        )
    assert result is sentinel
    mock.assert_awaited_once_with(business_name="BlueWave", city="Plano")


@pytest.mark.asyncio
async def test_verify_license_lowercase_state_still_routes() -> None:
    sentinel = LicenseStatus(found=True, license_number="OK")
    with patch.object(
        license_verifier,
        "verify_tx_license",
        AsyncMock(return_value=sentinel),
    ):
        result = await verify_license(
            state="tx", business_name="BlueWave", city=None
        )
    assert result.found is True


@pytest.mark.asyncio
async def test_verify_license_unsupported_state() -> None:
    for state in ("CA", "NY", "FL"):
        status = await verify_license(state=state, business_name="X")
        assert status.found is False
        assert status.status == "state_not_supported"
