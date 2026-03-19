from __future__ import annotations

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)

voice_app = FastAPI(title="SecretAIRY Voice")


@voice_app.get("/health")
def voice_health():
    return {"status": "ok", "service": "voice"}


@voice_app.post("/api/offer")
async def webrtc_offer():
    try:
        from .bot import create_bot

        task, transport = await create_bot()
        if task is None:
            return {"error": "Pipecat not installed. Install pipecat-ai to enable voice."}

        return {"status": "ready"}
    except Exception as e:
        logger.error("Voice session error: %s", e)
        return {"error": str(e)}
