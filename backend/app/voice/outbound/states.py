from enum import Enum


class OutboundCallState(str, Enum):
    INITIATING = "initiating"
    GREETING = "greeting"
    GATEKEEPER = "gatekeeper"
    PITCH = "pitch"
    QUESTIONS = "questions"
    SCHEDULING = "scheduling"
    VOICEMAIL = "voicemail"
    WRAPPING_UP = "wrapping_up"
    ENDED = "ended"
