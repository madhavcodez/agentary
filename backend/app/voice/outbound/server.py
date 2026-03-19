"""Outbound calling WebSocket server and Twilio webhook endpoints."""
from __future__ import annotations

import json
import logging
import traceback
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Request, WebSocket
from fastapi.responses import Response

from ...config import settings
from ...database import SessionLocal
from ...models.call_campaign import CallCampaign
from ...models.call_log import CallLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice/outbound", tags=["outbound"])


@router.api_route("/twiml/{campaign_id}", methods=["GET", "POST"])
def twiml_endpoint(campaign_id: UUID) -> Response:
    webhook_host = settings.twilio_webhook_base_url.replace("https://", "").replace("http://", "")

    # Load campaign script for the Say fallback opener
    db = SessionLocal()
    campaign = db.query(CallCampaign).filter(CallCampaign.id == campaign_id).first()
    opener = "Hello, this is SecretAIRY calling on behalf of Madhav Chauhan."
    if campaign and campaign.script_json:
        opener = campaign.script_json.get("opener", opener)
    db.close()

    # Say the opener first, then connect to the AI stream
    # The <Say> gives immediate audio feedback while the stream connects
    import html
    safe_opener = html.escape(opener)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f"  <Say voice=\"Polly.Joanna\">{safe_opener}</Say>\n"
        "  <Connect>\n"
        f'    <Stream url="wss://{webhook_host}/voice/outbound/ws/{campaign_id}" />\n'
        "  </Connect>\n"
        "</Response>"
    )
    return Response(content=xml, media_type="application/xml")


@router.api_route("/status/{campaign_id}", methods=["POST"])
async def status_callback(campaign_id: UUID, request: Request) -> dict:
    form = await request.form()
    call_status = form.get("CallStatus", "")
    call_sid = form.get("CallSid", "")
    call_duration = form.get("CallDuration")

    logger.info("Status callback: campaign=%s status=%s sid=%s", campaign_id, call_status, call_sid)

    db = SessionLocal()
    try:
        campaign = db.query(CallCampaign).filter(CallCampaign.id == campaign_id).first()
        if not campaign:
            return {"status": "ignored"}

        call_log = (
            db.query(CallLog)
            .filter(CallLog.campaign_id == campaign_id, CallLog.twilio_call_sid == call_sid)
            .first()
        )

        if call_status in ("completed", "failed", "busy", "no-answer", "canceled"):
            if call_log:
                call_log.ended_at = datetime.utcnow()
                if call_duration:
                    call_log.duration_sec = int(call_duration)
                outcome_map = {"completed": "connected", "failed": "failed", "busy": "busy", "no-answer": "no_answer", "canceled": "failed"}
                call_log.outcome = call_log.outcome or outcome_map.get(call_status, call_status)

            if call_status in ("failed", "busy", "no-answer", "canceled"):
                if campaign.attempt_count >= campaign.max_attempts:
                    campaign.status = "failed"
                else:
                    campaign.status = "pending"
            elif call_status == "completed":
                campaign.status = "completed"

            db.commit()
        return {"status": "ok"}
    finally:
        db.close()


@router.websocket("/ws/{campaign_id}")
async def outbound_ws(ws: WebSocket, campaign_id: UUID) -> None:
    await ws.accept()
    logger.info("=== OUTBOUND WS CONNECTED: campaign=%s ===", campaign_id)

    db = SessionLocal()
    stream_sid = None
    call_sid = None

    try:
        campaign = db.query(CallCampaign).filter(CallCampaign.id == campaign_id).first()
        if not campaign:
            logger.error("Campaign %s not found", campaign_id)
            await ws.close(code=1008)
            return

        # Wait for Twilio's start event to get stream_sid
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
                logger.info("Stream started: stream_sid=%s call_sid=%s", stream_sid, call_sid)
            elif event == "stop":
                logger.info("Stream stopped before start")
                return

        script = campaign.script_json or {}

        # Build system prompt from script
        from .prompts import build_system_prompt
        system_prompt = build_system_prompt(campaign, script)
        logger.info("System prompt built (%d chars)", len(system_prompt))

        # Create Pipecat pipeline components
        from pipecat.serializers.twilio import TwilioFrameSerializer
        from pipecat.transports.websocket.fastapi import FastAPIWebsocketTransport, FastAPIWebsocketParams
        from pipecat.services.google.gemini_live import GeminiLiveLLMService
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.pipeline.runner import PipelineRunner

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
            model="gemini-2.5-flash-native-audio-latest",
            voice_id="Aoede",
            system_instruction=system_prompt,
        )
        logger.info("GeminiLiveLLMService created")

        pipeline = Pipeline([transport.input(), llm, transport.output()])
        task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))
        logger.info("Pipeline built, running...")

        runner = PipelineRunner(handle_sigint=False, handle_sigterm=False)
        await runner.run(task)
        logger.info("Pipeline finished normally")

    except Exception as e:
        logger.error("=== OUTBOUND WS ERROR ===")
        logger.error(traceback.format_exc())
    finally:
        db.close()
        logger.info("=== OUTBOUND WS CLOSED: campaign=%s ===", campaign_id)
