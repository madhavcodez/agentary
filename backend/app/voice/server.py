"""SecretAIRY Voice Server — WebSocket-based conversational agent on port 7860.

Connects to Gemini for real-time conversation. Accepts text input over WebSocket
and streams back transcript entries. Browser mic capture can be layered on top.
"""
from __future__ import annotations

import asyncio
import json
import logging

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Add parent paths for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config import settings
from app.voice.conversation.states import CallState
from app.voice.conversation.state_machine import ConversationContext
from app.voice.policy.engine import PolicyEngine

logger = logging.getLogger(__name__)

voice_app = FastAPI(title="SecretAIRY Voice Agent")
voice_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SYSTEM_PROMPT = """You are SecretAIRY, an AI chief-of-staff and executive assistant for Madhav S Chauhan.

Your role:
- Answer questions about Madhav's professional background, skills, and experience
- Help with interview preparation and career guidance
- Discuss job matches and opportunities
- Provide information about Madhav's projects and expertise

Key facts about Madhav:
- AI/ML engineer and full-stack developer
- Skills: Python, TypeScript, React, FastAPI, PyTorch, Machine Learning, LLMs (Gemini, OpenAI), Vector DBs
- Projects: SoundScore (music app), SecretAIRY (AI chief-of-staff), Edward (AI scheduler), ReqChain (requirements platform)
- Looking for AI/ML or Full-Stack roles, new grad / 0-3 YOE
- Bay Area preferred, open to remote

Keep responses conversational, concise (2-4 sentences), and natural — as if speaking out loud.
If asked something you don't know, say so honestly."""

policy_engine = PolicyEngine()


async def get_gemini_response(messages: list[dict]) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)

    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=msg["text"])]))

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=300,
        ),
    )
    return response.text


@voice_app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info("Voice WebSocket connected")

    context = ConversationContext()
    messages: list[dict] = []

    # Send greeting
    greeting = "Hi! I'm SecretAIRY, Madhav's AI assistant. How can I help you today? You can ask me about his skills, projects, or career goals."
    await ws.send_json({
        "type": "transcript",
        "role": "agent",
        "text": greeting,
    })
    messages.append({"role": "agent", "text": greeting})
    context = context.transition(CallState.TRIAGE)

    try:
        while True:
            data = await ws.receive_text()

            try:
                parsed = json.loads(data)
                user_text = parsed.get("text", data)
            except json.JSONDecodeError:
                user_text = data

            if not user_text.strip():
                continue

            # Echo user message back for transcript
            await ws.send_json({
                "type": "transcript",
                "role": "user",
                "text": user_text,
            })
            messages.append({"role": "user", "text": user_text})

            # Policy check
            policy_result = policy_engine.evaluate_mid_call(user_text)
            if not policy_result["allowed"]:
                violation_msg = f"I'm sorry, I can't discuss that topic. ({', '.join(policy_result['violations'])})"
                await ws.send_json({
                    "type": "transcript",
                    "role": "agent",
                    "text": violation_msg,
                })
                messages.append({"role": "agent", "text": violation_msg})
                continue

            # Get Gemini response
            try:
                response_text = await get_gemini_response(messages)
                await ws.send_json({
                    "type": "transcript",
                    "role": "agent",
                    "text": response_text,
                })
                messages.append({"role": "agent", "text": response_text})
            except Exception as e:
                error_msg = f"Sorry, I had trouble processing that. Could you try again?"
                logger.error("Gemini error: %s", e)
                await ws.send_json({
                    "type": "transcript",
                    "role": "agent",
                    "text": error_msg,
                })

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception as e:
        logger.error("Voice WebSocket error: %s", e)


@voice_app.get("/health")
def health():
    return {"status": "ok", "service": "voice"}


if __name__ == "__main__":
    uvicorn.run(voice_app, host="0.0.0.0", port=7860)
