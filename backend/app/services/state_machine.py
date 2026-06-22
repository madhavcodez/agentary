"""Generic run lifecycle state machine.

Enforces valid state transitions across all run types (missions, crews,
workflows, voice, monitors, reports).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..models.enums import RunStatus


class InvalidTransition(Exception):
    """Raised when an attempted state transition is not allowed."""

    def __init__(self, current: RunStatus | str, target: RunStatus | str, reason: str | None = None) -> None:
        self.current = current
        self.target = target
        current_val = current.value if hasattr(current, "value") else str(current)
        target_val = target.value if hasattr(target, "value") else str(target)
        msg = f"Invalid transition: {current_val} -> {target_val}"
        if reason:
            msg += f" ({reason})"
        super().__init__(msg)


# Mapping of current_state -> set of allowed target_states
VALID_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.created: frozenset({RunStatus.queued, RunStatus.cancelled}),
    RunStatus.queued: frozenset({RunStatus.running, RunStatus.cancelled}),
    RunStatus.running: frozenset({
        RunStatus.completed,
        RunStatus.partially_failed,
        RunStatus.failed,
        RunStatus.cancelled,
        RunStatus.awaiting_input,
        RunStatus.retrying,
    }),
    RunStatus.retrying: frozenset({RunStatus.running, RunStatus.failed, RunStatus.cancelled}),
    RunStatus.awaiting_input: frozenset({RunStatus.running, RunStatus.cancelled}),
    RunStatus.partially_failed: frozenset({RunStatus.completed, RunStatus.failed}),
    # Terminal states have no valid outgoing transitions
    RunStatus.completed: frozenset(),
    RunStatus.failed: frozenset(),
    RunStatus.cancelled: frozenset(),
}

_TERMINAL_STATES: frozenset[RunStatus] = frozenset({
    RunStatus.completed,
    RunStatus.failed,
    RunStatus.cancelled,
})


# ── Call-specific state transitions ──────────────────────────────────

CALL_VALID_TRANSITIONS: dict[str, list[str]] = {
    "pending": ["ringing", "failed", "cancelled"],
    "ringing": ["connected", "no_answer", "voicemail", "failed"],
    "connected": ["completed", "failed"],
    "completed": [],  # terminal
    "failed": [],     # terminal
    "no_answer": [],  # terminal
    "voicemail": [],  # terminal
    "cancelled": [],  # terminal
}


def call_transition(current: str, target: str, reason: str | None = None) -> dict:
    """Validate and execute a call state transition.

    Args:
        current: The current call status (string).
        target: The desired next status (string).
        reason: Optional human-readable reason.

    Returns:
        A transition record dict.

    Raises:
        InvalidTransition: If the transition is not allowed.
    """
    current_val = current.value if hasattr(current, "value") else str(current)
    target_val = target.value if hasattr(target, "value") else str(target)
    allowed = CALL_VALID_TRANSITIONS.get(current_val, [])
    if target_val not in allowed:
        raise InvalidTransition(current_val, target_val)
    return {
        "from": current_val,
        "to": target_val,
        "timestamp": datetime.now(UTC).isoformat(),
        "reason": reason,
    }


def can_transition(current: RunStatus, target: RunStatus) -> bool:
    """Check whether a transition from *current* to *target* is allowed."""
    allowed = VALID_TRANSITIONS.get(current, frozenset())
    return target in allowed


def is_terminal(state: RunStatus) -> bool:
    """Return True if *state* is a terminal (no further transitions possible)."""
    return state in _TERMINAL_STATES


def transition(
    current_state: RunStatus,
    target_state: RunStatus,
    reason: str | None = None,
) -> dict[str, Any]:
    """Validate and execute a state transition.

    Args:
        current_state: The current run status.
        target_state: The desired next status.
        reason: Optional human-readable reason for the transition.

    Returns:
        A transition record dict with ``from``, ``to``, ``timestamp``, and
        ``reason`` keys.

    Raises:
        InvalidTransition: If the transition is not allowed.
    """
    if not can_transition(current_state, target_state):
        raise InvalidTransition(current_state, target_state, reason)

    return {
        "from": current_state.value,
        "to": target_state.value,
        "timestamp": datetime.now(UTC).isoformat(),
        "reason": reason,
    }
