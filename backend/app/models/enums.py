"""Shared enums used across all run types for the lifecycle state machine."""

import enum


class RunStatus(str, enum.Enum):
    created = "created"
    queued = "queued"
    running = "running"
    awaiting_input = "awaiting_input"
    retrying = "retrying"
    partially_failed = "partially_failed"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class FailureCategory(str, enum.Enum):
    transient_connector = "transient_connector"
    model_error = "model_error"
    rate_limited = "rate_limited"
    timeout = "timeout"
    validation = "validation"
    internal = "internal"
    cancelled = "cancelled"


class RunType(str, enum.Enum):
    mission = "mission"
    crew = "crew"
    workflow = "workflow"
    voice = "voice"
    monitor = "monitor"
    report = "report"
