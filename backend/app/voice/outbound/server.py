"""Outbound calling WebSocket server and Twilio webhook endpoints.

Connects Twilio Media Streams to Gemini Live via Pipecat for real-time
voice conversations. The pipeline:

    Twilio 8kHz mulaw <-> TwilioFrameSerializer <-> FastAPIWebsocketTransport
        <-> TranscriptCaptureProcessor <-> GeminiLiveLLMService (native audio)

TwilioFrameSerializer handles 8kHz <-> internal sample rate conversion.
The TranscriptCaptureProcessor sits inline and records both user speech
(TranscriptionFrame) and agent output (TTSTextFrame) so that a full
transcript is available when the pipeline finishes.
"""
from __future__ import annotations

import json
import logging
import time
import traceback
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response

from pipecat.frames.frames import (
    Frame,
    TTSTextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.serializers.twilio import TwilioFrameSerializer
from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

from ...config import settings
from ...database import SessionLocal
from ...models.call_campaign import CallCampaign
from ...models.call_log import CallLog
from ...services.call_post_processor import process_call_result
from .prompts import build_system_prompt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice/outbound", tags=["outbound"])


# ---------------------------------------------------------------------------
# Transcript capture processor
# ---------------------------------------------------------------------------

class TranscriptCaptureProcessor(FrameProcessor):
    """Captures user and agent text flowing through the pipeline.

    Sits inline and forwards every frame unchanged.  Records:
    - ``TranscriptionFrame`` -- user speech-to-text produced by Gemini Live.
    - ``TTSTextFrame`` -- final spoken agent text (one per sentence).

    We intentionally capture ``TTSTextFrame`` rather than the parent
    ``TextFrame`` because Gemini Live pushes *both* ``LLMTextFrame`` and
    ``TTSTextFrame`` with the same content; listening on ``TextFrame``
    would double-count every agent utterance.

    Call ``get_transcript()`` after the pipeline finishes to retrieve the
    full conversation.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._entries: list[dict] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Observe transcript-bearing frames and pass them through."""
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            self._entries.append({
                "role": "user",
                "text": frame.text,
                "timestamp": time.time(),
            })
            logger.debug("Transcript [user]: %s", frame.text)
        elif isinstance(frame, TTSTextFrame):
            self._entries.append({
                "role": "agent",
                "text": frame.text,
                "timestamp": time.time(),
            })
            logger.debug("Transcript [agent]: %s", frame.text)

        await self.push_frame(frame, direction)

    def get_transcript(self) -> str:
        """Return the accumulated transcript as a readable string."""
        lines: list[str] = []
        for entry in self._entries:
            label = "User" if entry["role"] == "user" else "Agent"
            lines.append(f"{label}: {entry['text']}")
        return "\n".join(lines)

    @property
    def has_content(self) -> bool:
        """Return True if at least one transcript entry was captured."""
        return len(self._entries) > 0


# ---------------------------------------------------------------------------
# TwiML endpoint — called by Twilio when the call connects
# ---------------------------------------------------------------------------

@router.api_route("/twiml/{campaign_id}", methods=["GET", "POST"])
def twiml_endpoint(campaign_id: UUID) -> Response:
    """Return TwiML that connects directly to the WebSocket stream.

    The ``<Say>`` element is intentionally omitted -- Gemini delivers the
    opener via its system_instruction so the greeting uses the same voice
    as the rest of the conversation and avoids a collision between Twilio
    TTS playback and the Media Stream connection.
    """
    webhook_host = (
        settings.twilio_webhook_base_url
        .replace("https://", "")
        .replace("http://", "")
    )

    logger.info(
        "TwiML requested: campaign=%s host=%s", campaign_id, webhook_host,
    )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        "  <Connect>\n"
        f'    <Stream url="wss://{webhook_host}/voice/outbound/ws/{campaign_id}" />\n'
        "  </Connect>\n"
        "</Response>"
    )
    return Response(content=xml, media_type="application/xml")


# ---------------------------------------------------------------------------
# Status callback — called by Twilio on call state transitions
# ---------------------------------------------------------------------------

@router.api_route("/status/{campaign_id}", methods=["POST"])
async def status_callback(campaign_id: UUID, request: Request) -> dict:
    """Handle Twilio status-change webhooks and update CallLog / CallCampaign."""
    form = await request.form()
    call_status = form.get("CallStatus", "")
    call_sid = form.get("CallSid", "")
    call_duration = form.get("CallDuration")

    logger.info(
        "Status callback: campaign=%s status=%s sid=%s",
        campaign_id, call_status, call_sid,
    )

    db = SessionLocal()
    try:
        campaign = db.query(CallCampaign).filter(
            CallCampaign.id == campaign_id,
        ).first()
        if not campaign:
            return {"status": "ignored"}

        call_log = (
            db.query(CallLog)
            .filter(
                CallLog.campaign_id == campaign_id,
                CallLog.twilio_call_sid == call_sid,
            )
            .first()
        )

        terminal_statuses = ("completed", "failed", "busy", "no-answer", "canceled")
        if call_status in terminal_statuses:
            if call_log:
                call_log.ended_at = datetime.utcnow()
                if call_duration:
                    call_log.duration_sec = int(call_duration)
                outcome_map = {
                    "completed": "connected",
                    "failed": "failed",
                    "busy": "busy",
                    "no-answer": "no_answer",
                    "canceled": "failed",
                }
                call_log.outcome = (
                    call_log.outcome or outcome_map.get(call_status, call_status)
                )

            if call_status in ("failed", "busy", "no-answer", "canceled"):
                if campaign.attempt_count >= campaign.max_attempts:
                    campaign.status = "failed"
                else:
                    campaign.status = "pending"
            elif call_status == "completed":
                campaign.status = "completed"

            db.commit()
        return {"status": "ok"}
    except Exception:
        logger.error("Status callback error:\n%s", traceback.format_exc())
        db.rollback()
        return {"status": "error"}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# WebSocket endpoint — receives the Twilio Media Stream
# ---------------------------------------------------------------------------

async def _save_transcript_and_post_process(
    db,
    campaign_id: UUID,
    call_sid: Optional[str],
    transcript_text: str,
) -> None:
    """Persist the transcript to the matching CallLog row and run post-processing.

    Post-processing uses Gemini to classify the call outcome, generate a
    summary, and optionally schedule a follow-up campaign.
    """
    if not call_sid or not transcript_text.strip():
        logger.info(
            "No transcript to save (call_sid=%s, text_len=%d)",
            call_sid,
            len(transcript_text) if transcript_text else 0,
        )
        return
    try:
        call_log = (
            db.query(CallLog)
            .filter(
                CallLog.campaign_id == campaign_id,
                CallLog.twilio_call_sid == call_sid,
            )
            .first()
        )
        if not call_log:
            logger.warning(
                "No CallLog found for call_sid=%s -- transcript not saved",
                call_sid,
            )
            return

        call_log.transcript = transcript_text
        db.commit()
        logger.info(
            "Transcript saved for call_sid=%s (%d chars)",
            call_sid,
            len(transcript_text),
        )

        # Run post-processing (classification, summary, follow-up scheduling)
        logger.info("Starting post-processing for call_sid=%s", call_sid)
        await process_call_result(db, call_log, transcript_text)
        logger.info("Post-processing complete for call_sid=%s", call_sid)

    except Exception:
        logger.error(
            "Failed to save transcript / post-process:\n%s",
            traceback.format_exc(),
        )
        db.rollback()


@router.websocket("/ws/{campaign_id}")
async def outbound_ws(ws: WebSocket, campaign_id: UUID) -> None:
    """Handle a Twilio Media Stream WebSocket for an outbound campaign call.

    Workflow:
    1. Accept the WebSocket connection.
    2. Read Twilio handshake events (``connected``, ``start``) to extract
       ``stream_sid`` and ``call_sid``.
    3. Build the Pipecat pipeline: Transport -> Gemini Live -> Transport.
    4. Run the pipeline until the call ends.
    5. Persist the captured transcript to the CallLog.
    """
    await ws.accept()
    logger.info("=== OUTBOUND WS CONNECTED: campaign=%s ===", campaign_id)

    db = SessionLocal()
    stream_sid: Optional[str] = None
    call_sid: Optional[str] = None
    transcript_capture: Optional[TranscriptCaptureProcessor] = None

    try:
        # ------------------------------------------------------------------
        # 1. Load campaign
        # ------------------------------------------------------------------
        campaign = db.query(CallCampaign).filter(
            CallCampaign.id == campaign_id,
        ).first()
        if not campaign:
            logger.error("Campaign %s not found", campaign_id)
            await ws.close(code=1008)
            return

        # ------------------------------------------------------------------
        # 2. Wait for Twilio handshake (connected -> start)
        # ------------------------------------------------------------------
        logger.info("Waiting for Twilio start event...")
        while stream_sid is None:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            event = msg.get("event")
            logger.info("Twilio event: %s", event)

            if event == "connected":
                continue
            elif event == "start":
                start_data = msg.get("start", {})
                stream_sid = start_data.get("streamSid")
                call_sid = start_data.get("callSid")
                logger.info(
                    "Stream started: stream_sid=%s call_sid=%s",
                    stream_sid, call_sid,
                )
            elif event == "stop":
                logger.info("Stream stopped before start — aborting")
                return

        if not stream_sid:
            logger.error("No stream_sid received — cannot build pipeline")
            return

        # ------------------------------------------------------------------
        # 3. Build system prompt
        # ------------------------------------------------------------------
        script = campaign.script_json or {}
        system_prompt = build_system_prompt(campaign, script)
        logger.info("System prompt built (%d chars)", len(system_prompt))

        # ------------------------------------------------------------------
        # 4. Construct Pipecat pipeline
        # ------------------------------------------------------------------
        serializer = TwilioFrameSerializer(
            stream_sid=stream_sid,
            call_sid=call_sid,
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
        )
        logger.info("TwilioFrameSerializer created")

        transport = FastAPIWebsocketTransport(
            websocket=ws,
            params=FastAPIWebsocketParams(serializer=serializer),
        )
        logger.info("FastAPIWebsocketTransport created")

        llm = GeminiLiveLLMService(
            api_key=settings.gemini_api_key,
            settings=GeminiLiveLLMService.Settings(
                model="models/gemini-2.5-flash-native-audio-preview-12-2025",
                voice="Kore",
            ),
            system_instruction=system_prompt,
            inference_on_context_initialization=True,
        )
        logger.info("GeminiLiveLLMService created")

        transcript_capture = TranscriptCaptureProcessor()

        pipeline = Pipeline([
            transport.input(),
            transcript_capture,
            llm,
            transport.output(),
        ])

        task = PipelineTask(
            pipeline,
            params=PipelineParams(
                audio_in_sample_rate=8000,
                audio_out_sample_rate=8000,
                allow_interruptions=True,
            ),
        )
        logger.info("Pipeline built — running...")

        # ------------------------------------------------------------------
        # 5. Run pipeline
        # ------------------------------------------------------------------
        runner = PipelineRunner(handle_sigint=False, handle_sigterm=False)
        await runner.run(task)
        logger.info("Pipeline finished normally")

    except Exception:
        logger.error("=== OUTBOUND WS ERROR ===\n%s", traceback.format_exc())
    finally:
        # ------------------------------------------------------------------
        # 6. Persist transcript, run post-processing, and clean up
        # ------------------------------------------------------------------
        if transcript_capture is not None and transcript_capture.has_content:
            transcript_text = transcript_capture.get_transcript()
            logger.info(
                "Transcript captured: %d chars, call_sid=%s",
                len(transcript_text),
                call_sid,
            )
            await _save_transcript_and_post_process(
                db, campaign_id, call_sid, transcript_text,
            )
        else:
            logger.info(
                "No transcript captured for campaign=%s call_sid=%s",
                campaign_id,
                call_sid,
            )

        db.close()
        logger.info("=== OUTBOUND WS CLOSED: campaign=%s ===", campaign_id)
