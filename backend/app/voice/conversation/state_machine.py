from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

from .states import CallState

STATE_PROMPTS = {
    CallState.GREETING: "You are SecretAIRY, an AI assistant for {name}. Greet the caller warmly and ask how you can help.",
    CallState.TRIAGE: "Determine what the caller needs. Ask clarifying questions if needed.",
    CallState.ANSWERING: "Answer the caller's question using the profile information available to you.",
    CallState.SCHEDULING: "Help schedule a meeting or follow-up. Confirm times and details.",
    CallState.TRANSFERRING: "Let the caller know you're transferring them to {name} directly.",
    CallState.VOICEMAIL: "Take a message for {name}. Get the caller's name, contact info, and reason for calling.",
    CallState.WRAPPING_UP: "Summarize what was discussed and confirm any next steps.",
    CallState.ENDED: "The call has ended.",
}


@dataclass(frozen=True)
class ConversationContext:
    state: CallState = CallState.GREETING
    caller_name: str | None = None
    caller_company: str | None = None
    topic: str | None = None
    history: tuple[str, ...] = field(default_factory=tuple)
    started_at: datetime = field(default_factory=datetime.utcnow)

    def transition(self, new_state: CallState, **updates) -> ConversationContext:
        return replace(self, state=new_state, **updates)

    def add_to_history(self, entry: str) -> ConversationContext:
        return replace(self, history=(*self.history, entry))

    def get_system_prompt(self, profile_name: str = "the user") -> str:
        template = STATE_PROMPTS.get(self.state, STATE_PROMPTS[CallState.GREETING])
        return template.format(name=profile_name)
