from __future__ import annotations

import logging

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


async def initiate_call(to_number: str, campaign_id: str, webhook_base_url: str) -> dict:
    """Initiate an outbound call via Twilio REST API.

    Args:
        to_number: E.164 phone number to call.
        campaign_id: UUID of the CallCampaign driving this call.
        webhook_base_url: The publicly accessible base URL (e.g. ngrok) that
            Twilio will use to fetch TwiML and receive status callbacks.

    Returns:
        Dict containing at minimum ``call_sid`` on success.

    Raises:
        httpx.HTTPStatusError: If Twilio returns a non-2xx response.
    """
    url = f"https://api.twilio.com/2010-04-01/Accounts/" f"{settings.twilio_account_sid}/Calls.json"
    twiml_url = f"{webhook_base_url}/voice/outbound/twiml/{campaign_id}"
    status_url = f"{webhook_base_url}/voice/outbound/status/{campaign_id}"

    payload = {
        "To": to_number,
        "From": settings.twilio_from_number,
        "Url": twiml_url,
        "StatusCallback": status_url,
        "StatusCallbackEvent": "initiated ringing answered completed",
        # NOTE: MachineDetection disabled — trial accounts play a message
        # that triggers false-positive voicemail detection and drops the call.
        # Re-enable after upgrading to a paid Twilio account.
        # "MachineDetection": "DetectMessageEnd",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            data=payload,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Twilio call initiated: SID=%s", data.get("sid"))
        return {"call_sid": data["sid"], "status": data.get("status", "queued")}


async def end_call(call_sid: str) -> None:
    """Terminate an active Twilio call.

    Args:
        call_sid: The Twilio Call SID to terminate.
    """
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/"
        f"{settings.twilio_account_sid}/Calls/{call_sid}.json"
    )
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            data={"Status": "completed"},
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )
        if response.status_code == 200:
            logger.info("Twilio call %s terminated", call_sid)
        elif response.status_code == 404:
            logger.debug("Twilio call %s already ended", call_sid)
        else:
            logger.error(
                "Failed to end call %s: %s %s",
                call_sid,
                response.status_code,
                response.text,
            )
