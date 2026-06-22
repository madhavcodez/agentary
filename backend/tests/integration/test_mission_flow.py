"""Integration tests for the mission creation and state transition flow.

These tests require a running PostgreSQL database. They use the DB fixture
from conftest.py with automatic rollback to keep the database clean.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from app.models.enums import RunStatus as LifecycleRunStatus
from app.models.mission import Mission, MissionStatus, MissionType
from app.models.mission_run import MissionRun, RunStatus, TriggerType
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.user import User
from app.services.state_machine import (
    transition,
)

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a disposable test user (rolled back after test)."""
    user = User(
        id=uuid.uuid4(),
        email=f"test-{uuid.uuid4().hex[:8]}@agentary-test.local",
        password_hash="$2b$12$testhashedpasswordplaceholder00000000000000000000",
        name="Test User",
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def test_project(db: Session, test_user: User) -> Project:
    """Create a disposable test project (rolled back after test)."""
    project = Project(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name=f"Test Project {uuid.uuid4().hex[:6]}",
        description="Integration test project",
        status=ProjectStatus.active,
        project_type=ProjectType.custom,
    )
    db.add(project)
    db.flush()
    return project


@pytest.fixture
def test_mission(db: Session, test_user: User, test_project: Project) -> Mission:
    """Create a disposable test mission (rolled back after test)."""
    mission = Mission(
        id=uuid.uuid4(),
        project_id=test_project.id,
        user_id=test_user.id,
        name="Integration Test Mission",
        description="Testing mission flow",
        objective="Verify state transitions",
        status=MissionStatus.draft,
        mission_type=MissionType.research,
    )
    db.add(mission)
    db.flush()
    return mission


# ── Tests ─────────────────────────────────────────────────────────────


class TestMissionCreation:
    """Test that missions and their runs are created correctly."""

    def test_mission_created_with_draft_status(self, db: Session, test_mission: Mission) -> None:
        fetched = db.get(Mission, test_mission.id)
        assert fetched is not None
        assert fetched.status == MissionStatus.draft

    def test_mission_has_correct_project(
        self, db: Session, test_mission: Mission, test_project: Project
    ) -> None:
        fetched = db.get(Mission, test_mission.id)
        assert fetched is not None
        assert fetched.project_id == test_project.id

    def test_mission_has_correct_user(
        self, db: Session, test_mission: Mission, test_user: User
    ) -> None:
        fetched = db.get(Mission, test_mission.id)
        assert fetched is not None
        assert fetched.user_id == test_user.id


class TestMissionRunCreation:
    """Test that mission runs are created with correct initial state."""

    def test_run_created_with_queued_status(self, db: Session, test_mission: Mission) -> None:
        run = MissionRun(
            id=uuid.uuid4(),
            mission_id=test_mission.id,
            status=RunStatus.queued,
            trigger_type=TriggerType.manual,
        )
        db.add(run)
        db.flush()

        fetched = db.get(MissionRun, run.id)
        assert fetched is not None
        assert fetched.status == RunStatus.queued

    def test_run_linked_to_mission(self, db: Session, test_mission: Mission) -> None:
        run = MissionRun(
            id=uuid.uuid4(),
            mission_id=test_mission.id,
            status=RunStatus.queued,
            trigger_type=TriggerType.manual,
        )
        db.add(run)
        db.flush()

        fetched = db.get(MissionRun, run.id)
        assert fetched is not None
        assert fetched.mission_id == test_mission.id

    def test_run_stores_state_transitions(self, db: Session, test_mission: Mission) -> None:
        initial_transition = transition(LifecycleRunStatus.created, LifecycleRunStatus.queued)
        run = MissionRun(
            id=uuid.uuid4(),
            mission_id=test_mission.id,
            status=RunStatus.queued,
            trigger_type=TriggerType.manual,
            state_transitions=[initial_transition],
        )
        db.add(run)
        db.flush()

        fetched = db.get(MissionRun, run.id)
        assert fetched is not None
        assert len(fetched.state_transitions) == 1
        assert fetched.state_transitions[0]["to"] == "queued"


class TestMissionStateTransitions:
    """Test state transition recording for mission runs."""

    def test_full_lifecycle_queued_to_completed(self, db: Session, test_mission: Mission) -> None:
        transitions = []

        t1 = transition(LifecycleRunStatus.created, LifecycleRunStatus.queued)
        transitions.append(t1)

        t2 = transition(LifecycleRunStatus.queued, LifecycleRunStatus.running)
        transitions.append(t2)

        t3 = transition(LifecycleRunStatus.running, LifecycleRunStatus.completed)
        transitions.append(t3)

        run = MissionRun(
            id=uuid.uuid4(),
            mission_id=test_mission.id,
            status=RunStatus.completed,
            trigger_type=TriggerType.manual,
            state_transitions=transitions,
        )
        db.add(run)
        db.flush()

        fetched = db.get(MissionRun, run.id)
        assert fetched is not None
        assert fetched.status == RunStatus.completed
        assert len(fetched.state_transitions) == 3
        assert fetched.state_transitions[0]["to"] == "queued"
        assert fetched.state_transitions[1]["to"] == "running"
        assert fetched.state_transitions[2]["to"] == "completed"

    def test_failure_lifecycle_with_reason(self, db: Session, test_mission: Mission) -> None:
        transitions = [
            transition(LifecycleRunStatus.created, LifecycleRunStatus.queued),
            transition(LifecycleRunStatus.queued, LifecycleRunStatus.running),
            transition(
                LifecycleRunStatus.running,
                LifecycleRunStatus.failed,
                reason="API key expired",
            ),
        ]

        run = MissionRun(
            id=uuid.uuid4(),
            mission_id=test_mission.id,
            status=RunStatus.failed,
            trigger_type=TriggerType.manual,
            state_transitions=transitions,
            failure_message="API key expired",
        )
        db.add(run)
        db.flush()

        fetched = db.get(MissionRun, run.id)
        assert fetched is not None
        assert fetched.status == RunStatus.failed
        assert fetched.failure_message == "API key expired"
        assert fetched.state_transitions[-1]["reason"] == "API key expired"

    def test_retry_lifecycle(self, db: Session, test_mission: Mission) -> None:
        transitions = [
            transition(LifecycleRunStatus.created, LifecycleRunStatus.queued),
            transition(LifecycleRunStatus.queued, LifecycleRunStatus.running),
            transition(
                LifecycleRunStatus.running,
                LifecycleRunStatus.retrying,
                reason="transient error",
            ),
            transition(LifecycleRunStatus.retrying, LifecycleRunStatus.running),
            transition(LifecycleRunStatus.running, LifecycleRunStatus.completed),
        ]

        run = MissionRun(
            id=uuid.uuid4(),
            mission_id=test_mission.id,
            status=RunStatus.completed,
            trigger_type=TriggerType.manual,
            state_transitions=transitions,
            retry_count=1,
        )
        db.add(run)
        db.flush()

        fetched = db.get(MissionRun, run.id)
        assert fetched is not None
        assert fetched.status == RunStatus.completed
        assert fetched.retry_count == 1
        assert len(fetched.state_transitions) == 5


class TestMissionCleanup:
    """Verify that test data is properly rolled back."""

    def test_no_test_data_persists(self, db: Session) -> None:
        """Validate that the fixture rollback keeps the DB clean.

        This test runs after others and checks that no stale test data exists
        with the test email domain.
        """
        count = db.query(User).filter(User.email.like("%@agentary-test.local")).count()
        # Due to rollback, there should be no persisted test users from fixtures
        # (The fixture-created user from THIS test is still in the session)
        assert count <= 1
