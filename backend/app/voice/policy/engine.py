from __future__ import annotations

from datetime import datetime

from .rules import BUSINESS_HOURS, FORBIDDEN_TOPICS, PII_PATTERNS


class PolicyEngine:
    def evaluate_pre_call(self, caller_info: dict) -> dict:
        violations: list[str] = []

        now = datetime.now()
        hour = now.hour
        if hour < BUSINESS_HOURS["start"] or hour >= BUSINESS_HOURS["end"]:
            violations.append(
                f"Outside business hours ({BUSINESS_HOURS['start']}:00-{BUSINESS_HOURS['end']}:00)"
            )

        return {
            "allowed": len(violations) == 0,
            "violations": violations,
        }

    def evaluate_mid_call(self, transcript: str) -> dict:
        violations: list[str] = []
        transcript_lower = transcript.lower()

        for topic in FORBIDDEN_TOPICS:
            if topic.lower() in transcript_lower:
                violations.append(f"Forbidden topic detected: {topic}")

        import re

        for pattern_name, pattern in PII_PATTERNS.items():
            if re.search(pattern, transcript):
                violations.append(f"PII detected: {pattern_name}")

        return {
            "allowed": len(violations) == 0,
            "violations": violations,
        }
