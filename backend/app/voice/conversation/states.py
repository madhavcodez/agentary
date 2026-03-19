from enum import Enum


class CallState(str, Enum):
    GREETING = "greeting"
    TRIAGE = "triage"
    ANSWERING = "answering"
    SCHEDULING = "scheduling"
    TRANSFERRING = "transferring"
    VOICEMAIL = "voicemail"
    WRAPPING_UP = "wrapping_up"
    ENDED = "ended"
