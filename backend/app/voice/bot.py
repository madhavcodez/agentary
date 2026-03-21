from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Agentary, an AI research assistant for Madhav S Chauhan.

Your role:
- Answer questions about Madhav's professional background, skills, and experience
- Help schedule meetings and manage inquiries
- Take messages when Madhav is unavailable
- Provide information about Madhav's projects and expertise

You are warm, professional, and efficient. Keep responses concise and natural for voice conversation.

Key facts about Madhav:
- AI/ML engineer and full-stack developer
- Skills: Python, TypeScript, React, FastAPI, Machine Learning, LLMs
- Looking for AI/ML or Full-Stack roles, new grad / 0-3 YOE
- Bay Area preferred, open to remote

If someone asks about scheduling, take their details and say you'll coordinate with Madhav.
If someone asks about topics you don't know, offer to take a message."""


async def create_bot():
    try:
        from pipecat.transports.services.small_webrtc import SmallWebRTCTransport
        from pipecat.services.google import GoogleLLMService
        from pipecat.vad.silero import SileroVADAnalyzer
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.task import PipelineParams, PipelineTask

        from .config import voice_settings
        from .tools.registry import register_all_tools

        transport = SmallWebRTCTransport()

        llm = GoogleLLMService(
            model=voice_settings.voice_model,
            api_key=voice_settings.gemini_api_key or None,
            voice_id=voice_settings.voice_name,
            system_instruction=SYSTEM_PROMPT,
        )

        register_all_tools(llm)

        pipeline = Pipeline([
            transport.input(),
            SileroVADAnalyzer(),
            llm,
            transport.output(),
        ])

        task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))
        return task, transport

    except ImportError as e:
        logger.warning("Pipecat not installed. Voice features unavailable: %s", e)
        return None, None
