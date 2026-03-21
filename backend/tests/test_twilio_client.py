from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx


@pytest.fixture
def mock_settings():
    with patch("app.services.twilio_client.settings") as mock:
        mock.twilio_account_sid = "ACtest123"
        mock.twilio_auth_token = "testtoken456"
        mock.twilio_from_number = "+15551234567"
        mock.twilio_webhook_base_url = "https://example.ngrok.io"
        yield mock


class TestInitiateCall:
    @pytest.mark.asyncio
    async def test_initiate_call_success(self, mock_settings):
        """Verify that initiate_call POSTs to Twilio with correct parameters."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "sid": "CA_test_sid_123",
            "status": "queued",
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.twilio_client import initiate_call

            result = await initiate_call(
                to_number="+15559876543",
                campaign_id="campaign-uuid-123",
                webhook_base_url="https://example.ngrok.io",
            )

            assert result["call_sid"] == "CA_test_sid_123"
            assert result["status"] == "queued"

            # Verify the POST was called with correct URL
            call_args = mock_client_instance.post.call_args
            url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
            assert "Calls.json" in url
            assert "ACtest123" in url

            # Verify form data
            data = call_args[1].get("data", {})
            assert data["To"] == "+15559876543"
            assert data["From"] == "+15551234567"
            assert "twiml" in data["Url"]
            assert "campaign-uuid-123" in data["Url"]
            # MachineDetection disabled for trial accounts
            assert "MachineDetection" not in data

    @pytest.mark.asyncio
    async def test_initiate_call_http_error(self, mock_settings):
        """Verify that HTTP errors are raised."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Unauthorized",
                request=MagicMock(),
                response=mock_response,
            )
        )

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.twilio_client import initiate_call

            with pytest.raises(httpx.HTTPStatusError):
                await initiate_call(
                    to_number="+15559876543",
                    campaign_id="campaign-uuid-123",
                    webhook_base_url="https://example.ngrok.io",
                )


class TestEndCall:
    @pytest.mark.asyncio
    async def test_end_call_success(self, mock_settings):
        """Verify that end_call POSTs Status=completed to Twilio."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.twilio_client import end_call

            await end_call("CA_test_sid_123")

            call_args = mock_client_instance.post.call_args
            url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
            assert "CA_test_sid_123" in url
            data = call_args[1].get("data", {})
            assert data["Status"] == "completed"

    @pytest.mark.asyncio
    async def test_end_call_already_ended(self, mock_settings):
        """Verify that 404 is handled gracefully (call already ended)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from app.services.twilio_client import end_call

            # Should not raise
            await end_call("CA_test_sid_123")
