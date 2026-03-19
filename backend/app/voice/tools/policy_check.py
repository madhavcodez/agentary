from __future__ import annotations

from ..policy.engine import PolicyEngine

_engine = PolicyEngine()


async def check_pre_call(caller_info: dict) -> dict:
    return _engine.evaluate_pre_call(caller_info)


async def check_mid_call(transcript_segment: str) -> dict:
    return _engine.evaluate_mid_call(transcript_segment)
