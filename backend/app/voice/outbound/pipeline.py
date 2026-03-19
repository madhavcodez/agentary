from __future__ import annotations

import logging
from typing import Any

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.google.gemini_live import GeminiLiveLLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from ...config import settings
from .prompts import build_system_prompt

logger = logging.getLogger(__name__)


async def create_outbound_pipeline(
    ws,
    campaign: Any,
    script: dict[str, Any],
    stream_sid: str,
    call_sid: str,
) -> PipelineTask:
    """Build a Pipecat pipeline for an outbound Twilio call.

    The pipeline connects the Twilio Media Stream (via WebSocket) to Google
    Gemini Live for real-time voice conversation.

    Args:
        ws: The FastAPI WebSocket connection (already accepted).
        campaign: The CallCampaign ORM object driving this call.
        script: The generated call script dict.
        stream_sid: Twilio's Media Stream SID from the ``start`` event.
        call_sid: Twilio's Call SID.

    Returns:
        A PipelineTask ready to be run.
    """
    system_prompt = build_system_prompt(campaign, script)

    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        account_sid=settings.twilio_account_sid,
        auth_token=settings.twilio_auth_token,
    )

    transport = FastAPIWebsocketTransport(
        websocket=ws,
        params=FastAPIWebsocketParams(serializer=serializer),
    )

    llm = GeminiLiveLLMService(
        api_key=settings.gemini_api_key,
        system_instruction=system_prompt,
        settings=GeminiLiveLLMService.Settings(
            model="gemini-2.5-flash-native-audio-preview",
            voice="Aoede",
        ),
    )

    pipeline = Pipeline([transport.input(), llm, transport.output()])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
        ),
    )

    return task
