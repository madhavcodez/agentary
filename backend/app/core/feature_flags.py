from __future__ import annotations

# Simple feature flag system — all features default to True (enabled).
# Override via environment variables or a future admin panel.

FEATURE_FLAGS: dict[str, bool] = {
    "projects": True,
    "missions": True,
    "expert_agents": True,
    "voice_extraction": True,
    "workflows": True,
    "monitors": True,
    "reports": True,
    "datasets": True,
    "findings": True,
    "knowledge_base": True,
    "sources": True,
    "live_feed": True,
    "audit_log": True,
    "scheduled_missions": True,
    "voice_calling": True,
    "web_research": True,
    "data_extraction": True,
}


def is_enabled(feature: str) -> bool:
    return FEATURE_FLAGS.get(feature, False)


def set_flag(feature: str, enabled: bool) -> None:
    FEATURE_FLAGS[feature] = enabled
