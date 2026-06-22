"""Unit tests for the run lifecycle state machine."""

import pytest

from app.models.enums import RunStatus
from app.services.state_machine import (
    InvalidTransition,
    can_transition,
    is_terminal,
    transition,
)


class TestTransition:
    """Tests for the transition() function."""

    def test_valid_transition_created_to_queued(self) -> None:
        result = transition(RunStatus.created, RunStatus.queued)
        assert result["from"] == "created"
        assert result["to"] == "queued"
        assert "timestamp" in result

    def test_valid_transition_queued_to_running(self) -> None:
        result = transition(RunStatus.queued, RunStatus.running)
        assert result["to"] == "running"

    def test_valid_transition_running_to_completed(self) -> None:
        result = transition(RunStatus.running, RunStatus.completed)
        assert result["to"] == "completed"

    def test_valid_transition_running_to_failed(self) -> None:
        result = transition(RunStatus.running, RunStatus.failed)
        assert result["to"] == "failed"

    def test_valid_transition_running_to_partially_failed(self) -> None:
        result = transition(RunStatus.running, RunStatus.partially_failed)
        assert result["to"] == "partially_failed"

    def test_valid_transition_running_to_retrying(self) -> None:
        result = transition(RunStatus.running, RunStatus.retrying)
        assert result["to"] == "retrying"

    def test_valid_transition_running_to_cancelled(self) -> None:
        result = transition(RunStatus.running, RunStatus.cancelled)
        assert result["to"] == "cancelled"

    def test_valid_transition_retrying_to_running(self) -> None:
        result = transition(RunStatus.retrying, RunStatus.running)
        assert result["to"] == "running"

    def test_valid_transition_running_to_awaiting_input(self) -> None:
        result = transition(RunStatus.running, RunStatus.awaiting_input)
        assert result["to"] == "awaiting_input"

    def test_valid_transition_awaiting_input_to_running(self) -> None:
        result = transition(RunStatus.awaiting_input, RunStatus.running)
        assert result["to"] == "running"

    def test_valid_transition_partially_failed_to_completed(self) -> None:
        result = transition(RunStatus.partially_failed, RunStatus.completed)
        assert result["to"] == "completed"

    def test_valid_transition_partially_failed_to_failed(self) -> None:
        result = transition(RunStatus.partially_failed, RunStatus.failed)
        assert result["to"] == "failed"

    def test_valid_transition_created_to_cancelled(self) -> None:
        result = transition(RunStatus.created, RunStatus.cancelled)
        assert result["to"] == "cancelled"

    def test_valid_transition_retrying_to_failed(self) -> None:
        result = transition(RunStatus.retrying, RunStatus.failed)
        assert result["to"] == "failed"

    def test_valid_transition_retrying_to_cancelled(self) -> None:
        result = transition(RunStatus.retrying, RunStatus.cancelled)
        assert result["to"] == "cancelled"


class TestInvalidTransitions:
    """Tests for invalid state transitions."""

    def test_invalid_transition_completed_to_running(self) -> None:
        with pytest.raises(InvalidTransition):
            transition(RunStatus.completed, RunStatus.running)

    def test_invalid_transition_failed_to_running(self) -> None:
        with pytest.raises(InvalidTransition):
            transition(RunStatus.failed, RunStatus.running)

    def test_invalid_transition_created_to_completed(self) -> None:
        with pytest.raises(InvalidTransition):
            transition(RunStatus.created, RunStatus.completed)

    def test_invalid_transition_cancelled_to_running(self) -> None:
        with pytest.raises(InvalidTransition):
            transition(RunStatus.cancelled, RunStatus.running)

    def test_invalid_transition_created_to_running(self) -> None:
        with pytest.raises(InvalidTransition):
            transition(RunStatus.created, RunStatus.running)

    def test_invalid_transition_queued_to_completed(self) -> None:
        with pytest.raises(InvalidTransition):
            transition(RunStatus.queued, RunStatus.completed)

    def test_invalid_transition_completed_to_failed(self) -> None:
        with pytest.raises(InvalidTransition):
            transition(RunStatus.completed, RunStatus.failed)


class TestCanTransition:
    """Tests for the can_transition() predicate."""

    def test_can_transition_true(self) -> None:
        assert can_transition(RunStatus.created, RunStatus.queued) is True

    def test_can_transition_false(self) -> None:
        assert can_transition(RunStatus.completed, RunStatus.running) is False

    def test_can_transition_running_to_all_valid_targets(self) -> None:
        valid_targets = [
            RunStatus.completed,
            RunStatus.partially_failed,
            RunStatus.failed,
            RunStatus.cancelled,
            RunStatus.awaiting_input,
            RunStatus.retrying,
        ]
        for target in valid_targets:
            assert can_transition(RunStatus.running, target) is True

    def test_can_transition_terminal_to_anything_is_false(self) -> None:
        terminals = [RunStatus.completed, RunStatus.failed, RunStatus.cancelled]
        for terminal in terminals:
            for target in RunStatus:
                assert can_transition(terminal, target) is False


class TestIsTerminal:
    """Tests for the is_terminal() predicate."""

    def test_is_terminal_completed(self) -> None:
        assert is_terminal(RunStatus.completed) is True

    def test_is_terminal_failed(self) -> None:
        assert is_terminal(RunStatus.failed) is True

    def test_is_terminal_cancelled(self) -> None:
        assert is_terminal(RunStatus.cancelled) is True

    def test_is_terminal_running(self) -> None:
        assert is_terminal(RunStatus.running) is False

    def test_is_terminal_created(self) -> None:
        assert is_terminal(RunStatus.created) is False

    def test_is_terminal_queued(self) -> None:
        assert is_terminal(RunStatus.queued) is False

    def test_is_terminal_retrying(self) -> None:
        assert is_terminal(RunStatus.retrying) is False


class TestTransitionMetadata:
    """Tests for transition record metadata."""

    def test_transition_includes_reason(self) -> None:
        result = transition(
            RunStatus.running, RunStatus.failed, reason="timeout exceeded"
        )
        assert result["reason"] == "timeout exceeded"

    def test_transition_reason_none_by_default(self) -> None:
        result = transition(RunStatus.created, RunStatus.queued)
        assert result["reason"] is None

    def test_transition_records_timestamp_iso(self) -> None:
        result = transition(RunStatus.created, RunStatus.queued)
        # ISO format contains a T separator
        assert "T" in result["timestamp"]

    def test_transition_from_field_is_value(self) -> None:
        result = transition(RunStatus.created, RunStatus.queued)
        assert result["from"] == "created"
        assert isinstance(result["from"], str)

    def test_transition_to_field_is_value(self) -> None:
        result = transition(RunStatus.queued, RunStatus.running)
        assert result["to"] == "running"
        assert isinstance(result["to"], str)


class TestInvalidTransitionError:
    """Tests for the InvalidTransition exception attributes."""

    def test_exception_has_current_and_target(self) -> None:
        with pytest.raises(InvalidTransition) as exc_info:
            transition(RunStatus.completed, RunStatus.running)
        assert exc_info.value.current == RunStatus.completed
        assert exc_info.value.target == RunStatus.running

    def test_exception_message_contains_states(self) -> None:
        with pytest.raises(InvalidTransition, match=r"completed.*running"):
            transition(RunStatus.completed, RunStatus.running)
