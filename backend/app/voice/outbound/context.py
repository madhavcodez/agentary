from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from .states import OutboundCallState


@dataclass(frozen=True)
class OutboundCallContext:
    """Immutable context for an outbound call conversation.

    Every mutation returns a new instance — the original is never changed.
    """

    state: OutboundCallState = OutboundCallState.INITIATING
    contact_name: str | None = None
    contact_title: str | None = None
    company: str = ""
    opportunity_title: str = ""
    match_score: float = 0.0
    talking_points: tuple[str, ...] = field(default_factory=tuple)
    voicemail_detected: bool = False
    callback_proposed: bool = False
    history: tuple[str, ...] = field(default_factory=tuple)
    started_at: datetime = field(default_factory=datetime.utcnow)

    def transition(self, new_state: OutboundCallState, **updates) -> OutboundCallContext:
        """Return a new context with the state changed and optional field updates."""
        return replace(self, state=new_state, **updates)

    def add_to_history(self, entry: str) -> OutboundCallContext:
        """Return a new context with an additional history entry."""
        return replace(self, history=(*self.history, entry))
