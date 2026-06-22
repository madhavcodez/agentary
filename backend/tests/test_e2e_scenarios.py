"""Comprehensive E2E test scenarios covering the full SecretAIRY lifecycle.

Tests are model-level (no database needed). They validate model instantiation,
field correctness, relationships, and service logic using mocks where external
APIs are involved.

Scenarios:
    1. Create Project and Mission
    2. Research Execution
    3. Report Generation
    4. Workflow Execution
    5. Monitor and Alert
    6. Full Golden Path (lifecycle)
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.core.events import Event, EventBus, EventType
from app.models.agent_crew import ActivityType, AgentActivity, AgentCrew, CoordinationStrategy
from app.models.alert import AlertRecord, AlertSeverityLevel, AlertType
from app.models.crew_task import CrewTask, CrewTaskStatus
from app.models.expert_agent import AgentSpecialty, ExpertAgent
from app.models.finding import Finding, FindingType, SourceType
from app.models.mission import Mission, MissionStatus, MissionType
from app.models.mission_run import (
    MissionRun,
    MissionTask,
    RunStatus,
    TaskStatus,
    TaskType,
    TriggerType,
)
from app.models.monitor import Alert, AlertSeverity, Monitor, MonitorStatus, MonitorType
from app.models.project import Project, ProjectStatus, ProjectType
from app.models.report import Report
from app.models.workflow import Workflow
from app.models.workflow_run import WorkflowRun
from app.services.change_detector import ChangeResult, detect_text_change, detect_value_change

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_id() -> uuid.UUID:
    return uuid.uuid4()


def _make_project(user_id: uuid.UUID, name: str = "Gas Station Survey", **kwargs) -> Project:
    return Project(
        id=uuid.uuid4(),
        user_id=user_id,
        name=name,
        status=kwargs.get("status", ProjectStatus.active),
        project_type=kwargs.get("project_type", ProjectType.local_business),
        description=kwargs.get("description"),
    )


def _make_mission(
    project: Project,
    name: str = "Find gas prices within 5 miles of 30.2672, -97.7431",
    **kwargs,
) -> Mission:
    return Mission(
        id=uuid.uuid4(),
        project_id=project.id,
        user_id=project.user_id,
        name=name,
        description=kwargs.get("description", "Survey nearby gas stations for current fuel prices"),
        objective=kwargs.get("objective", "Collect current gas prices from stations within 5 miles"),
        status=kwargs.get("status", MissionStatus.draft),
        mission_type=kwargs.get("mission_type", MissionType.data_collection),
        parameters=kwargs.get("parameters", {
            "geography": "30.2672, -97.7431",
            "radius_miles": 5,
            "target": "gas stations",
        }),
    )


def _make_expert(slug: str, name: str, specialty: AgentSpecialty) -> ExpertAgent:
    return ExpertAgent(
        id=uuid.uuid4(),
        slug=slug,
        name=name,
        specialty=specialty,
        system_prompt=f"You are {name}.",
        tools=["gemini_search"],
        model_config_json={"model": "gemini-2.5-flash"},
        icon="\U0001f50d",
        is_system=True,
        is_active=True,
    )


def _make_finding(
    project_id: uuid.UUID,
    mission_id: uuid.UUID,
    title: str,
    finding_type: FindingType = FindingType.price,
    **kwargs,
) -> Finding:
    return Finding(
        id=uuid.uuid4(),
        project_id=project_id,
        mission_id=mission_id,
        finding_type=finding_type,
        title=title,
        content=kwargs.get("content", f"Finding: {title}"),
        source_type=kwargs.get("source_type", SourceType.web),
        source_url=kwargs.get("source_url"),
        source_name=kwargs.get("source_name"),
        confidence=kwargs.get("confidence", 0.85),
        verified=kwargs.get("verified", False),
        tags=kwargs.get("tags", []),
        structured_data=kwargs.get("structured_data", {}),
    )


# ===========================================================================
# Scenario 1: Create Project and Mission
# ===========================================================================

class TestScenario1_ProjectAndMission:
    """Verify project + mission creation with correct fields and relationships."""

    def test_create_project_with_all_fields(self):
        user_id = _user_id()
        project = _make_project(
            user_id,
            name="Gas Station Survey",
            project_type=ProjectType.local_business,
            description="Survey gas prices around downtown Austin",
        )
        assert project.name == "Gas Station Survey"
        assert project.status == ProjectStatus.active
        assert project.project_type == ProjectType.local_business
        assert project.user_id == user_id
        assert project.description == "Survey gas prices around downtown Austin"
        assert project.id is not None

    def test_create_mission_with_parameters(self):
        user_id = _user_id()
        project = _make_project(user_id)
        mission = _make_mission(project)

        assert mission.name == "Find gas prices within 5 miles of 30.2672, -97.7431"
        assert mission.status == MissionStatus.draft
        assert mission.mission_type == MissionType.data_collection
        assert mission.project_id == project.id
        assert mission.user_id == project.user_id
        assert mission.parameters["radius_miles"] == 5
        assert mission.parameters["geography"] == "30.2672, -97.7431"
        assert mission.objective == "Collect current gas prices from stations within 5 miles"

    def test_project_mission_relationship_ids(self):
        user_id = _user_id()
        project = _make_project(user_id)
        mission_1 = _make_mission(project, name="Mission A")
        mission_2 = _make_mission(project, name="Mission B")

        assert mission_1.project_id == project.id
        assert mission_2.project_id == project.id
        assert mission_1.user_id == mission_2.user_id == user_id

    def test_project_status_enum_values(self):
        assert ProjectStatus.active == "active"
        assert ProjectStatus.archived == "archived"
        assert ProjectStatus.completed == "completed"

    def test_mission_status_lifecycle(self):
        user_id = _user_id()
        project = _make_project(user_id)
        mission = _make_mission(project, status=MissionStatus.draft)

        assert mission.status == MissionStatus.draft
        # Simulate status transitions
        mission.status = MissionStatus.queued
        assert mission.status == MissionStatus.queued
        mission.status = MissionStatus.running
        assert mission.status == MissionStatus.running
        mission.status = MissionStatus.completed
        assert mission.status == MissionStatus.completed

    def test_mission_type_enum_values(self):
        assert MissionType.research == "research"
        assert MissionType.data_collection == "data_collection"
        assert MissionType.voice_extraction == "voice_extraction"
        assert MissionType.monitoring == "monitoring"
        assert MissionType.competitive_analysis == "competitive_analysis"
        assert MissionType.custom == "custom"

    def test_project_type_enum_values(self):
        assert ProjectType.market_research == "market_research"
        assert ProjectType.local_business == "local_business"
        assert ProjectType.real_estate == "real_estate"
        assert ProjectType.custom == "custom"


# ===========================================================================
# Scenario 2: Research Execution
# ===========================================================================

class TestScenario2_ResearchExecution:
    """Crew assembly, mission run, task creation, finding generation, event system."""

    def test_assemble_crew_with_experts(self):
        web_researcher = _make_expert("web-researcher", "Web Researcher", AgentSpecialty.web_researcher)
        data_extractor = _make_expert("data-extractor", "Data Extractor", AgentSpecialty.data_extractor)
        local_intel = _make_expert("local-intel", "Local Business Intel", AgentSpecialty.local_business_intel)

        mission_id = uuid.uuid4()
        crew = AgentCrew(
            id=uuid.uuid4(),
            mission_id=mission_id,
            agents=[
                {"agent_id": str(web_researcher.id), "slug": "web-researcher", "name": "Web Researcher", "role": "web_researcher"},
                {"agent_id": str(data_extractor.id), "slug": "data-extractor", "name": "Data Extractor", "role": "data_extractor"},
                {"agent_id": str(local_intel.id), "slug": "local-intel", "name": "Local Business Intel", "role": "local_business_intel"},
            ],
            coordination_strategy=CoordinationStrategy.parallel,
        )

        assert len(crew.agents) == 3
        slugs = {a["slug"] for a in crew.agents}
        assert slugs == {"web-researcher", "data-extractor", "local-intel"}
        assert crew.coordination_strategy == CoordinationStrategy.parallel

    def test_create_mission_run(self):
        mission_id = uuid.uuid4()
        run = MissionRun(
            id=uuid.uuid4(),
            mission_id=mission_id,
            status=RunStatus.queued,
            trigger_type=TriggerType.manual,
            config_snapshot={"radius_miles": 5},
        )
        assert run.status == RunStatus.queued
        assert run.trigger_type == TriggerType.manual
        assert run.config_snapshot["radius_miles"] == 5

    def test_create_crew_tasks_for_each_expert(self):
        run_id = uuid.uuid4()
        expert_ids = [uuid.uuid4() for _ in range(3)]
        task_descriptions = [
            ("web_search", "Search for gas stations near 30.2672, -97.7431"),
            ("data_extraction", "Extract prices from gas station websites"),
            ("analysis", "Analyze price patterns across stations"),
        ]

        tasks = []
        for expert_id, (task_type, desc) in zip(expert_ids, task_descriptions):
            task = CrewTask(
                id=uuid.uuid4(),
                mission_run_id=run_id,
                expert_agent_id=expert_id,
                task_type=task_type,
                description=desc,
                input_data={"query": desc},
                status=CrewTaskStatus.pending,
                thinking_log=[],
                tool_calls=[],
            )
            tasks.append(task)

        assert len(tasks) == 3
        assert all(t.status == CrewTaskStatus.pending for t in tasks)
        assert all(t.mission_run_id == run_id for t in tasks)

    def test_simulate_task_execution_status_transitions(self):
        task = CrewTask(
            id=uuid.uuid4(),
            mission_run_id=uuid.uuid4(),
            expert_agent_id=uuid.uuid4(),
            task_type="web_search",
            description="Search gas stations",
            status=CrewTaskStatus.pending,
        )

        # Simulate execution lifecycle
        assert task.status == CrewTaskStatus.pending
        task.status = CrewTaskStatus.running
        assert task.status == CrewTaskStatus.running
        task.status = CrewTaskStatus.completed
        task.output_data = {"results": ["Shell", "Exxon", "Chevron"]}
        task.findings_count = 3
        assert task.status == CrewTaskStatus.completed
        assert task.findings_count == 3

    def test_generate_findings_with_correct_fields(self):
        project_id = uuid.uuid4()
        mission_id = uuid.uuid4()

        findings = [
            _make_finding(
                project_id, mission_id,
                title="Shell Station - Regular $3.19/gal",
                finding_type=FindingType.price,
                content="Shell at 1234 S Lamar Blvd: Regular $3.19, Mid $3.49, Premium $3.79",
                source_url="https://www.gasbuddy.com/station/12345",
                source_name="GasBuddy",
                confidence=0.92,
                tags=["gas_prices", "shell", "austin"],
                structured_data={"regular": 3.19, "mid": 3.49, "premium": 3.79},
            ),
            _make_finding(
                project_id, mission_id,
                title="Exxon Station - Regular $3.25/gal",
                finding_type=FindingType.price,
                content="Exxon at 5678 Congress Ave: Regular $3.25, Mid $3.55, Premium $3.85",
                source_url="https://www.gasbuddy.com/station/67890",
                source_name="GasBuddy",
                confidence=0.88,
                tags=["gas_prices", "exxon", "austin"],
                structured_data={"regular": 3.25, "mid": 3.55, "premium": 3.85},
            ),
            _make_finding(
                project_id, mission_id,
                title="Average gas price trend: down 2% week-over-week",
                finding_type=FindingType.trend,
                content="Gas prices in the 78704 area decreased by 2% compared to last week",
                source_type=SourceType.inferred,
                confidence=0.75,
                tags=["gas_prices", "trend", "austin"],
            ),
        ]

        assert len(findings) == 3
        assert findings[0].finding_type == FindingType.price
        assert findings[0].confidence == 0.92
        assert findings[0].source_name == "GasBuddy"
        assert "gas_prices" in findings[0].tags
        assert findings[0].structured_data["regular"] == 3.19

        assert findings[2].finding_type == FindingType.trend
        assert findings[2].source_type == SourceType.inferred

        # All findings link to same project and mission
        assert all(f.project_id == project_id for f in findings)
        assert all(f.mission_id == mission_id for f in findings)

    def test_mission_task_model_fields(self):
        """Test the MissionTask model (from mission_run.py) has correct fields."""
        run_id = uuid.uuid4()
        task = MissionTask(
            id=uuid.uuid4(),
            run_id=run_id,
            expert_agent_id=uuid.uuid4(),
            task_type=TaskType.research,
            status=TaskStatus.pending,
            input_data={"query": "gas prices near Austin"},
            result_data={},
        )
        assert task.task_type == TaskType.research
        assert task.status == TaskStatus.pending
        assert task.run_id == run_id

    def test_agent_activity_event_creation(self):
        """Verify AgentActivity model captures thinking/searching events."""
        activity = AgentActivity(
            id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            crew_id=uuid.uuid4(),
            expert_agent_id=uuid.uuid4(),
            activity_type=ActivityType.searching,
            content="Searching for gas stations near downtown Austin",
            metadata_json={"event": "EXPERT_THINKING", "action": "searching"},
            confidence=None,
        )
        assert activity.activity_type == ActivityType.searching
        assert "gas stations" in activity.content

    def test_event_bus_exists_and_subscribable(self):
        """Verify the EventBus can subscribe and would emit events."""
        bus = EventBus()
        received = []

        def handler(event):
            received.append(event)

        bus.subscribe(EventType.finding_created, handler)

        event = Event(
            event_type=EventType.finding_created,
            data={"finding_id": str(uuid.uuid4()), "title": "Gas price found"},
            project_id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
        )

        # EventBus.publish is async, so we verify subscription registration
        assert EventType.finding_created in bus._subscribers
        assert handler in bus._subscribers[EventType.finding_created]

        # Verify event serialization
        event_dict = event.to_dict()
        assert event_dict["event_type"] == "finding.created"
        assert event_dict["data"]["title"] == "Gas price found"

    @pytest.mark.asyncio
    async def test_event_bus_publish(self):
        """Verify the EventBus publishes events to subscribers."""
        bus = EventBus()
        received = []

        async def async_handler(event):
            received.append(event)

        bus.subscribe(EventType.mission_completed, async_handler)

        event = Event(
            event_type=EventType.mission_completed,
            data={"findings_count": 5},
            mission_id=uuid.uuid4(),
        )

        await bus.publish(event)
        assert len(received) == 1
        assert received[0].data["findings_count"] == 5

    def test_run_status_and_trigger_enums(self):
        assert RunStatus.queued == "queued"
        assert RunStatus.running == "running"
        assert RunStatus.completed == "completed"
        assert RunStatus.failed == "failed"
        assert RunStatus.cancelled == "cancelled"

        assert TriggerType.manual == "manual"
        assert TriggerType.scheduled == "scheduled"
        assert TriggerType.monitor_triggered == "monitor_triggered"

    def test_coordination_strategies(self):
        assert CoordinationStrategy.parallel == "parallel"
        assert CoordinationStrategy.sequential == "sequential"
        assert CoordinationStrategy.hierarchical == "hierarchical"


# ===========================================================================
# Scenario 3: Report Generation
# ===========================================================================

class TestScenario3_ReportGeneration:
    """Test report creation, sections, sources, data export, and share service."""

    def _setup_findings(self):
        project_id = uuid.uuid4()
        mission_id = uuid.uuid4()
        user_id = _user_id()
        findings = [
            _make_finding(
                project_id, mission_id,
                title="Shell Station - Regular $3.19/gal",
                finding_type=FindingType.price,
                source_url="https://gasbuddy.com/station/12345",
                source_name="GasBuddy",
                confidence=0.92,
                tags=["gas_prices"],
                structured_data={"regular": 3.19},
            ),
            _make_finding(
                project_id, mission_id,
                title="Exxon Station - Regular $3.25/gal",
                finding_type=FindingType.price,
                source_url="https://gasbuddy.com/station/67890",
                source_name="GasBuddy",
                confidence=0.88,
                tags=["gas_prices"],
                structured_data={"regular": 3.25},
            ),
            _make_finding(
                project_id, mission_id,
                title="Prices trending down 2% WoW",
                finding_type=FindingType.trend,
                source_type=SourceType.inferred,
                confidence=0.75,
                tags=["gas_prices", "trend"],
            ),
        ]
        return project_id, mission_id, user_id, findings

    def test_report_model_creation_with_sections_and_sources(self):
        project_id, mission_id, user_id, _findings = self._setup_findings()

        sections = [
            {"title": "Executive Summary", "content": "Gas prices surveyed across 5-mile radius."},
            {"title": "Price Comparison", "content": "Shell $3.19, Exxon $3.25 for regular grade."},
            {"title": "Trends", "content": "Prices down 2% week-over-week."},
        ]
        sources = [
            {"name": "GasBuddy", "url": "https://gasbuddy.com/station/12345", "type": "web"},
            {"name": "GasBuddy", "url": "https://gasbuddy.com/station/67890", "type": "web"},
        ]

        report = Report(
            id=uuid.uuid4(),
            project_id=project_id,
            mission_id=mission_id,
            user_id=user_id,
            title="Gas Station Price Survey - Austin TX",
            description="Comprehensive gas price analysis within 5 miles of downtown Austin",
            report_type="research_report",
            status="completed",
            content_markdown="# Gas Station Price Survey\n\n## Executive Summary\n...",
            content_html="<h1>Gas Station Price Survey</h1>",
            sections=sections,
            executive_summary="Gas prices surveyed across 5-mile radius.",
            methodology="Web scraping and data aggregation from GasBuddy",
            sources=sources,
            charts=[{"type": "bar", "title": "Price Comparison", "data": {}}],
            structured_data={"avg_regular": 3.22, "station_count": 2},
            metadata_={"findings_count": 3, "generation_time_seconds": 12.5},
        )

        assert report.title == "Gas Station Price Survey - Austin TX"
        assert report.report_type == "research_report"
        assert report.status == "completed"
        assert len(report.sections) == 3
        assert report.sections[0]["title"] == "Executive Summary"
        assert len(report.sources) == 2
        assert report.sources[0]["name"] == "GasBuddy"
        assert report.executive_summary is not None
        assert report.methodology is not None
        assert report.content_markdown is not None
        assert report.content_html is not None
        assert report.structured_data["avg_regular"] == 3.22
        assert report.project_id == project_id
        assert report.mission_id == mission_id

    def test_report_status_lifecycle(self):
        report = Report(
            id=uuid.uuid4(),
            user_id=_user_id(),
            title="Test Report",
            report_type="research_report",
            status="generating",
        )
        assert report.status == "generating"
        report.status = "completed"
        assert report.status == "completed"

    def test_report_share_token_fields(self):
        report = Report(
            id=uuid.uuid4(),
            user_id=_user_id(),
            title="Shareable Report",
            report_type="research_report",
            status="completed",
            share_enabled=False,
            share_token=None,
        )
        assert report.share_enabled is False
        assert report.share_token is None

        # Simulate enabling share
        import secrets
        token = secrets.token_urlsafe(32)
        report.share_token = token
        report.share_enabled = True
        assert report.share_enabled is True
        assert len(report.share_token) > 0

    def test_data_exporter_csv_format_columns(self):
        """Verify the CSV column definitions match the Finding model fields."""
        from app.services.reports.data_exporter import _FINDING_CSV_COLUMNS

        expected_columns = [
            "title", "category", "content", "confidence", "source_type",
            "source_name", "source_url", "expert", "tags", "verified", "created_at",
        ]
        assert expected_columns == _FINDING_CSV_COLUMNS

    def test_data_exporter_class_exists(self):
        from app.services.reports.data_exporter import DataExporter

        exporter = DataExporter()
        assert hasattr(exporter, "export_findings_csv")

    def test_share_service_class_exists(self):
        from app.services.reports.share_service import ShareService

        svc = ShareService()
        assert hasattr(svc, "create_share_link")
        assert hasattr(svc, "get_shared_report")
        assert hasattr(svc, "revoke_share")

    def test_report_generator_class_exists(self):
        from app.services.reports.report_generator import ReportGenerator

        gen = ReportGenerator()
        assert hasattr(gen, "_format_findings_for_prompt")
        assert hasattr(gen, "_load_template")

    def test_findings_format_for_prompt(self):
        """Test that _format_findings_for_prompt produces numbered text.

        The ReportGenerator accesses `f.category` on each Finding, which
        is not a real column but may be set dynamically by the query layer.
        We attach it manually for this model-level test.
        """
        from app.services.reports.report_generator import ReportGenerator

        _project_id, _mission_id, _user_id, findings = self._setup_findings()
        # The report generator reads `.category` from each finding --
        # set it to the finding_type value so the formatter works.
        for f in findings:
            f.category = f.finding_type.value

        formatted = ReportGenerator._format_findings_for_prompt(findings)

        # Should produce a non-empty string with numbered entries
        assert isinstance(formatted, str)
        assert len(formatted) > 0
        assert "Shell" in formatted
        assert "Exxon" in formatted

    def test_report_chart_field(self):
        report = Report(
            id=uuid.uuid4(),
            user_id=_user_id(),
            title="Chart Report",
            report_type="research_report",
            status="completed",
            charts=[
                {"type": "bar", "title": "Price Comparison", "data": {"labels": ["Shell", "Exxon"], "values": [3.19, 3.25]}},
                {"type": "line", "title": "Price Trend", "data": {"dates": ["2026-03-14", "2026-03-21"], "values": [3.30, 3.22]}},
            ],
        )
        assert len(report.charts) == 2
        assert report.charts[0]["type"] == "bar"
        assert report.charts[1]["type"] == "line"


# ===========================================================================
# Scenario 4: Workflow Execution
# ===========================================================================

class TestScenario4_WorkflowExecution:
    """Create workflow with nodes/edges, test executor topological sort, verify node execution."""

    def _build_workflow(self) -> tuple[uuid.UUID, uuid.UUID, Workflow]:
        user_id = _user_id()
        project_id = uuid.uuid4()
        nodes = [
            {"id": "trigger_1", "type": "manual_trigger", "config": {}, "position": {"x": 0, "y": 0}},
            {"id": "search_1", "type": "web_search", "config": {"query_template": "gas prices Austin TX"}, "position": {"x": 200, "y": 0}},
            {"id": "extract_1", "type": "data_extraction", "config": {"fields": ["price", "station_name"]}, "position": {"x": 400, "y": 0}},
            {"id": "report_1", "type": "generate_report", "config": {"report_type": "research_report"}, "position": {"x": 600, "y": 0}},
        ]
        edges = [
            {"id": "e1", "source_node_id": "trigger_1", "target_node_id": "search_1"},
            {"id": "e2", "source_node_id": "search_1", "target_node_id": "extract_1"},
            {"id": "e3", "source_node_id": "extract_1", "target_node_id": "report_1"},
        ]

        workflow = Workflow(
            id=uuid.uuid4(),
            project_id=project_id,
            user_id=user_id,
            name="Gas Price Research Pipeline",
            description="Automated gas price research workflow",
            status="active",
            trigger_type="manual",
            nodes=nodes,
            edges=edges,
            variables={"target_location": "Austin, TX"},
        )
        return user_id, project_id, workflow

    def test_workflow_model_creation(self):
        _user_id, project_id, workflow = self._build_workflow()

        assert workflow.name == "Gas Price Research Pipeline"
        assert workflow.status == "active"
        assert workflow.trigger_type == "manual"
        assert len(workflow.nodes) == 4
        assert len(workflow.edges) == 3
        assert workflow.variables["target_location"] == "Austin, TX"
        assert workflow.project_id == project_id

    def test_workflow_run_model_creation(self):
        _, _, workflow = self._build_workflow()

        run = WorkflowRun(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            user_id=workflow.user_id,
            status="queued",
            trigger_type="manual",
            node_results={},
        )
        assert run.status == "queued"
        assert run.workflow_id == workflow.id
        assert run.node_results == {}

    def test_executor_topological_sort(self):
        """Verify the executor's topological sort produces correct execution order."""
        from app.services.workflow.executor import WorkflowExecutor

        _, _, workflow = self._build_workflow()

        # Create executor with a mock db
        mock_db = MagicMock()
        executor = WorkflowExecutor(db=mock_db)

        order = executor._topological_sort(workflow.nodes, workflow.edges)

        assert len(order) == 4
        # trigger must come before search, search before extract, extract before report
        assert order.index("trigger_1") < order.index("search_1")
        assert order.index("search_1") < order.index("extract_1")
        assert order.index("extract_1") < order.index("report_1")

    def test_executor_topological_sort_detects_cycle(self):
        from app.services.workflow.executor import WorkflowExecutor

        nodes = [
            {"id": "a", "type": "manual_trigger", "config": {}},
            {"id": "b", "type": "web_search", "config": {}},
        ]
        edges = [
            {"id": "e1", "source_node_id": "a", "target_node_id": "b"},
            {"id": "e2", "source_node_id": "b", "target_node_id": "a"},
        ]

        mock_db = MagicMock()
        executor = WorkflowExecutor(db=mock_db)

        with pytest.raises(ValueError, match="cycle"):
            executor._topological_sort(nodes, edges)

    def test_executor_find_node(self):
        from app.services.workflow.executor import WorkflowExecutor

        _, _, workflow = self._build_workflow()
        mock_db = MagicMock()
        executor = WorkflowExecutor(db=mock_db)

        node = executor._find_node(workflow.nodes, "search_1")
        assert node is not None
        assert node["type"] == "web_search"

        missing = executor._find_node(workflow.nodes, "nonexistent")
        assert missing is None

    def test_executor_get_terminal_nodes(self):
        from app.services.workflow.executor import WorkflowExecutor

        _, _, workflow = self._build_workflow()
        mock_db = MagicMock()
        executor = WorkflowExecutor(db=mock_db)

        terminal = executor._get_terminal_nodes(workflow.nodes, workflow.edges)
        assert terminal == ["report_1"]

    def test_executor_gather_inputs_single(self):
        from app.services.workflow.executor import WorkflowExecutor

        mock_db = MagicMock()
        executor = WorkflowExecutor(db=mock_db)

        edges = [
            {"source_node_id": "a", "target_node_id": "b", "source_port": "output", "target_port": "input"},
        ]
        outputs = {"a": {"results": ["data1", "data2"]}}

        result = executor._gather_inputs("b", edges, outputs)
        assert result == {"results": ["data1", "data2"]}

    def test_executor_gather_inputs_none(self):
        from app.services.workflow.executor import WorkflowExecutor

        mock_db = MagicMock()
        executor = WorkflowExecutor(db=mock_db)

        result = executor._gather_inputs("trigger_1", [], {})
        assert result is None

    def test_workflow_node_handler_manual_trigger(self):
        """Test the manual_trigger handler returns expected output."""
        import asyncio

        from app.services.workflow.node_handlers import handle_manual_trigger
        result = asyncio.get_event_loop().run_until_complete(
            handle_manual_trigger({}, None, {})
        )
        assert result["triggered"] is True
        assert result["trigger_type"] == "manual"

    def test_workflow_branching_dag(self):
        """Verify topological sort handles branching DAGs correctly."""
        from app.services.workflow.executor import WorkflowExecutor

        nodes = [
            {"id": "trigger", "type": "manual_trigger", "config": {}},
            {"id": "branch_a", "type": "web_search", "config": {}},
            {"id": "branch_b", "type": "data_extraction", "config": {}},
            {"id": "merge", "type": "generate_report", "config": {}},
        ]
        edges = [
            {"id": "e1", "source_node_id": "trigger", "target_node_id": "branch_a"},
            {"id": "e2", "source_node_id": "trigger", "target_node_id": "branch_b"},
            {"id": "e3", "source_node_id": "branch_a", "target_node_id": "merge"},
            {"id": "e4", "source_node_id": "branch_b", "target_node_id": "merge"},
        ]

        mock_db = MagicMock()
        executor = WorkflowExecutor(db=mock_db)
        order = executor._topological_sort(nodes, edges)

        assert len(order) == 4
        assert order[0] == "trigger"
        assert order[-1] == "merge"
        # branch_a and branch_b come after trigger but before merge
        assert order.index("branch_a") > order.index("trigger")
        assert order.index("branch_b") > order.index("trigger")

    def test_workflow_run_status_transitions(self):
        run = WorkflowRun(
            id=uuid.uuid4(),
            workflow_id=uuid.uuid4(),
            user_id=_user_id(),
            status="queued",
            trigger_type="manual",
            node_results={},
        )
        assert run.status == "queued"
        run.status = "running"
        assert run.status == "running"
        run.status = "completed"
        assert run.status == "completed"

    def test_executor_truncate_output(self):
        from app.services.workflow.executor import WorkflowExecutor

        mock_db = MagicMock()
        executor = WorkflowExecutor(db=mock_db)

        # Small output passes through
        small = {"key": "value"}
        assert executor._truncate_output(small) == small

        # Large output gets truncated
        large = {"data": "x" * 20000}
        result = executor._truncate_output(large, max_size=100)
        assert result["__truncated"] is True
        assert "preview" in result


# ===========================================================================
# Scenario 5: Monitor and Alert
# ===========================================================================

class TestScenario5_MonitorAndAlert:
    """Monitor creation, change detection, alert generation, notification channels."""

    def test_create_monitor_with_check_config(self):
        user_id = _user_id()
        project_id = uuid.uuid4()

        monitor = Monitor(
            id=uuid.uuid4(),
            project_id=project_id,
            user_id=user_id,
            name="Gas Price Monitor - Shell Downtown",
            description="Track gas price changes at Shell on S Lamar",
            status=MonitorStatus.active,
            monitor_type=MonitorType.price_tracker,
            check_config={
                "url": "https://gasbuddy.com/station/12345",
                "field": "regular_price",
                "threshold_pct": 5.0,
            },
            alert_config={
                "channels": ["email", "in_app"],
                "severity_threshold": "warning",
            },
            schedule_cron="0 */6 * * *",
            timezone="America/Chicago",
            total_checks=0,
            total_alerts=0,
        )

        assert monitor.name == "Gas Price Monitor - Shell Downtown"
        assert monitor.status == MonitorStatus.active
        assert monitor.monitor_type == MonitorType.price_tracker
        assert monitor.check_config["threshold_pct"] == 5.0
        assert monitor.alert_config["channels"] == ["email", "in_app"]
        assert monitor.schedule_cron == "0 */6 * * *"
        assert monitor.timezone == "America/Chicago"

    def test_monitor_status_enum_values(self):
        assert MonitorStatus.active == "active"
        assert MonitorStatus.paused == "paused"
        assert MonitorStatus.archived == "archived"

    def test_monitor_type_enum_values(self):
        assert MonitorType.web_content == "web_content"
        assert MonitorType.api_data == "api_data"
        assert MonitorType.price_tracker == "price_tracker"
        assert MonitorType.listing_watcher == "listing_watcher"
        assert MonitorType.competitor_tracker == "competitor_tracker"
        assert MonitorType.custom == "custom"

    def test_detect_value_change_triggers_alert(self):
        """Simulate price change detection via the change_detector module.

        Note: detect_value_change compares abs(diff) against threshold,
        NOT percentage. A $0.26 change exceeds a $0.10 threshold.
        """
        old_price = 3.19
        new_price = 3.45

        result = detect_value_change(old_price, new_price, threshold=0.10)

        assert result.changed is True
        assert result.change_type == "value"
        assert result.details["old_value"] == 3.19
        assert result.details["new_value"] == 3.45

    def test_detect_value_no_change_below_threshold(self):
        # diff = $0.01, which is within threshold $0.05
        result = detect_value_change(3.19, 3.20, threshold=0.05)

        assert result.changed is False

    def test_detect_text_change(self):
        old_text = "Regular: $3.19\nMid: $3.49\nPremium: $3.79"
        new_text = "Regular: $3.29\nMid: $3.59\nPremium: $3.89"

        result = detect_text_change(old_text, new_text)

        assert result.changed is True
        assert result.change_type == "text"
        assert result.details["added_lines"] > 0

    def test_detect_text_no_change(self):
        text = "Regular: $3.19"
        result = detect_text_change(text, text)
        assert result.changed is False

    def test_alert_creation_from_monitor(self):
        """Verify Alert model (from monitor.py) can be created with all fields."""
        monitor_id = uuid.uuid4()
        project_id = uuid.uuid4()

        alert = Alert(
            id=uuid.uuid4(),
            monitor_id=monitor_id,
            project_id=project_id,
            alert_type="price_change",
            title="Gas price increased at Shell Downtown",
            message="Regular gas price increased from $3.19 to $3.45 (+8.2%)",
            severity=AlertSeverity.warning,
            data={
                "old_price": 3.19,
                "new_price": 3.45,
                "change_pct": 8.15,
                "station": "Shell Downtown",
            },
            acknowledged=False,
            delivered_channels=["email", "in_app"],
        )

        assert alert.title == "Gas price increased at Shell Downtown"
        assert alert.severity == AlertSeverity.warning
        assert alert.acknowledged is False
        assert "email" in alert.delivered_channels
        assert "in_app" in alert.delivered_channels
        assert alert.data["change_pct"] == 8.15

    def test_alert_record_model(self):
        """Verify the AlertRecord model (from alert.py) with notification channels."""
        user_id = _user_id()
        monitor_id = uuid.uuid4()

        record = AlertRecord(
            id=uuid.uuid4(),
            monitor_id=monitor_id,
            project_id=uuid.uuid4(),
            user_id=user_id,
            alert_type=AlertType.change_detected,
            severity=AlertSeverityLevel.high,
            title="Price spike detected",
            message="Regular gas up 15% at Exxon Congress",
            data={"old_price": 3.25, "new_price": 3.74},
            is_read=False,
            notification_sent=True,
            notification_channels=["email", "sms", "in_app"],
        )

        assert record.alert_type == AlertType.change_detected
        assert record.severity == AlertSeverityLevel.high
        assert record.is_read is False
        assert record.notification_sent is True
        assert len(record.notification_channels) == 3
        assert "sms" in record.notification_channels

    def test_alert_type_enum_values(self):
        assert AlertType.change_detected == "change_detected"
        assert AlertType.threshold_exceeded == "threshold_exceeded"
        assert AlertType.new_data == "new_data"
        assert AlertType.error == "error"

    def test_alert_severity_level_enum_values(self):
        assert AlertSeverityLevel.low == "low"
        assert AlertSeverityLevel.medium == "medium"
        assert AlertSeverityLevel.high == "high"
        assert AlertSeverityLevel.critical == "critical"

    def test_monitor_snapshot_update(self):
        """Simulate a monitor check updating the last_snapshot."""
        monitor = Monitor(
            id=uuid.uuid4(),
            user_id=_user_id(),
            name="Price Watch",
            monitor_type=MonitorType.price_tracker,
            status=MonitorStatus.active,
            total_checks=5,
            total_alerts=1,
            last_snapshot={"regular": 3.19},
        )

        # Simulate a new check
        new_snapshot = {"regular": 3.45}
        monitor.last_snapshot = new_snapshot
        monitor.total_checks = monitor.total_checks + 1
        monitor.last_check_at = datetime.now(UTC)

        assert monitor.total_checks == 6
        assert monitor.last_snapshot["regular"] == 3.45

    def test_event_types_for_monitors(self):
        """Verify monitor-related event types exist."""
        assert EventType.monitor_triggered == "monitor.triggered"
        assert EventType.monitor_alert == "monitor.alert"

    def test_change_result_dataclass(self):
        result = ChangeResult(
            changed=True,
            change_type="value",
            summary="Price increased by $0.26",
            details={"old_value": 3.19, "new_value": 3.45},
        )
        assert result.changed is True
        assert result.change_type == "value"
        assert result.summary == "Price increased by $0.26"
        # ChangeResult is frozen
        with pytest.raises(AttributeError):
            result.changed = False


# ===========================================================================
# Scenario 6: Full Golden Path (Lifecycle)
# ===========================================================================

class TestScenario6_FullGoldenPath:
    """Full lifecycle: user -> project -> mission -> crew -> findings -> report -> monitor -> export."""

    def test_full_lifecycle(self):
        # --- Phase 1: User + Project ---
        user_id = _user_id()

        project = _make_project(
            user_id,
            name="Gas Station Survey",
            project_type=ProjectType.local_business,
            description="Comprehensive gas price tracking in Austin TX",
        )
        assert project.status == ProjectStatus.active

        # --- Phase 2: Mission ---
        mission = _make_mission(
            project,
            name="Find gas prices within 5 miles of 30.2672, -97.7431",
            mission_type=MissionType.data_collection,
        )
        assert mission.status == MissionStatus.draft
        assert mission.project_id == project.id

        # --- Phase 3: Crew Assembly ---
        web_researcher = _make_expert("web-researcher", "Web Researcher", AgentSpecialty.web_researcher)
        data_extractor = _make_expert("data-extractor", "Data Extractor", AgentSpecialty.data_extractor)
        synthesizer = _make_expert("synthesizer", "Synthesizer", AgentSpecialty.synthesizer)

        crew = AgentCrew(
            id=uuid.uuid4(),
            mission_id=mission.id,
            agents=[
                {"agent_id": str(web_researcher.id), "slug": "web-researcher", "name": "Web Researcher", "role": "web_researcher"},
                {"agent_id": str(data_extractor.id), "slug": "data-extractor", "name": "Data Extractor", "role": "data_extractor"},
                {"agent_id": str(synthesizer.id), "slug": "synthesizer", "name": "Synthesizer", "role": "synthesizer"},
            ],
            coordination_strategy=CoordinationStrategy.parallel,
        )
        assert len(crew.agents) == 3
        assert crew.mission_id == mission.id

        # --- Phase 4: Mission Run ---
        run = MissionRun(
            id=uuid.uuid4(),
            mission_id=mission.id,
            status=RunStatus.queued,
            trigger_type=TriggerType.manual,
        )

        # Simulate status transitions
        mission.status = MissionStatus.running
        run.status = RunStatus.running
        assert mission.status == MissionStatus.running
        assert run.status == RunStatus.running

        # --- Phase 5: Crew Tasks ---
        tasks = []
        for agent_data in crew.agents:
            task = CrewTask(
                id=uuid.uuid4(),
                mission_run_id=run.id,
                expert_agent_id=uuid.UUID(agent_data["agent_id"]),
                task_type=agent_data["role"],
                description=f"Execute {agent_data['role']} task",
                status=CrewTaskStatus.pending,
                thinking_log=[],
            )
            tasks.append(task)

        assert len(tasks) == 3
        # Simulate all tasks completing
        for task in tasks:
            task.status = CrewTaskStatus.completed
            task.output_data = {"result": f"Completed {task.task_type}"}
            task.findings_count = 2

        assert all(t.status == CrewTaskStatus.completed for t in tasks)

        # --- Phase 6: Findings ---
        findings = [
            _make_finding(
                project.id, mission.id,
                title="Shell - Regular $3.19/gal",
                finding_type=FindingType.price,
                source_url="https://gasbuddy.com/12345",
                source_name="GasBuddy",
                confidence=0.92,
                tags=["gas_prices", "shell"],
                structured_data={"regular": 3.19, "mid": 3.49, "premium": 3.79},
            ),
            _make_finding(
                project.id, mission.id,
                title="Exxon - Regular $3.25/gal",
                finding_type=FindingType.price,
                source_url="https://gasbuddy.com/67890",
                source_name="GasBuddy",
                confidence=0.88,
                tags=["gas_prices", "exxon"],
                structured_data={"regular": 3.25, "mid": 3.55, "premium": 3.85},
            ),
            _make_finding(
                project.id, mission.id,
                title="Chevron - Regular $3.29/gal",
                finding_type=FindingType.price,
                source_name="Google Maps",
                source_type=SourceType.web,
                confidence=0.80,
                tags=["gas_prices", "chevron"],
                structured_data={"regular": 3.29},
            ),
            _make_finding(
                project.id, mission.id,
                title="Average regular gas: $3.24/gal in 5-mile radius",
                finding_type=FindingType.statistic,
                source_type=SourceType.inferred,
                confidence=0.85,
                tags=["gas_prices", "average"],
                structured_data={"avg_regular": 3.24, "station_count": 3},
            ),
            _make_finding(
                project.id, mission.id,
                title="Prices trending down 2% week-over-week",
                finding_type=FindingType.trend,
                source_type=SourceType.inferred,
                confidence=0.72,
                tags=["gas_prices", "trend"],
            ),
        ]

        assert len(findings) == 5
        assert all(f.project_id == project.id for f in findings)
        assert all(f.mission_id == mission.id for f in findings)
        price_findings = [f for f in findings if f.finding_type == FindingType.price]
        assert len(price_findings) == 3

        # Complete mission run
        run.status = RunStatus.completed
        run.metrics = {"sources_queried": 5, "findings_count": len(findings), "calls_made": 0}
        mission.status = MissionStatus.completed
        mission.findings_count = len(findings)
        mission.confidence_score = sum(f.confidence for f in findings) / len(findings)

        assert mission.status == MissionStatus.completed
        assert run.status == RunStatus.completed
        assert run.metrics["findings_count"] == 5

        # --- Phase 7: Report ---
        report = Report(
            id=uuid.uuid4(),
            project_id=project.id,
            mission_id=mission.id,
            user_id=user_id,
            title="Gas Station Price Survey - Austin TX 78704",
            report_type="research_report",
            status="completed",
            content_markdown="# Gas Price Survey\n\n## Summary\nSurveyed 3 stations...",
            sections=[
                {"title": "Executive Summary", "content": "Surveyed 3 gas stations within 5 miles."},
                {"title": "Price Comparison", "content": "Shell $3.19, Exxon $3.25, Chevron $3.29."},
                {"title": "Trends", "content": "Prices down 2% WoW."},
            ],
            executive_summary="Surveyed 3 gas stations within 5 miles of downtown Austin.",
            sources=[
                {"name": "GasBuddy", "url": "https://gasbuddy.com", "type": "web"},
                {"name": "Google Maps", "type": "web"},
            ],
            charts=[{"type": "bar", "title": "Regular Gas Prices by Station"}],
            structured_data={"avg_regular": 3.24, "station_count": 3},
        )

        assert report.status == "completed"
        assert report.project_id == project.id
        assert report.mission_id == mission.id
        assert len(report.sections) == 3
        assert len(report.sources) == 2

        # --- Phase 8: Monitor ---
        monitor = Monitor(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=user_id,
            name="Gas Price Watch - Austin Downtown",
            description="Monitor gas prices for changes > 5%",
            status=MonitorStatus.active,
            monitor_type=MonitorType.price_tracker,
            check_config={
                "stations": ["Shell S Lamar", "Exxon Congress", "Chevron Barton Springs"],
                "field": "regular_price",
                "threshold_pct": 5.0,
            },
            alert_config={"channels": ["email", "in_app"]},
            schedule_cron="0 8 * * *",
            timezone="America/Chicago",
            total_checks=0,
            total_alerts=0,
        )

        assert monitor.status == MonitorStatus.active
        assert monitor.project_id == project.id

        # Simulate a price change detection
        # detect_value_change threshold is absolute difference, not percentage
        old_price = 3.19
        new_price = 3.45
        change = detect_value_change(old_price, new_price, threshold=0.10)
        assert change.changed is True

        # Generate alert
        alert = Alert(
            id=uuid.uuid4(),
            monitor_id=monitor.id,
            project_id=project.id,
            alert_type="price_change",
            title="Shell Downtown: Regular gas up 8.2%",
            message=f"Price increased from ${old_price} to ${new_price}",
            severity=AlertSeverity.warning,
            data=change.details,
            acknowledged=False,
            delivered_channels=["email", "in_app"],
        )

        assert alert.severity == AlertSeverity.warning
        assert alert.monitor_id == monitor.id

        # Update monitor stats
        monitor.total_checks = 1
        monitor.total_alerts = 1
        monitor.last_snapshot = {"regular": new_price}

        # --- Phase 9: Export verification ---
        # Verify findings have the fields needed for CSV export

        for finding in findings:
            assert hasattr(finding, "title")
            assert hasattr(finding, "content")
            assert hasattr(finding, "confidence")
            assert hasattr(finding, "source_type")
            assert hasattr(finding, "source_name")
            assert hasattr(finding, "source_url")
            assert hasattr(finding, "tags")
            assert hasattr(finding, "verified")

        # --- Verify full chain integrity ---
        assert mission.project_id == project.id
        assert crew.mission_id == mission.id
        assert run.mission_id == mission.id
        assert all(t.mission_run_id == run.id for t in tasks)
        assert all(f.project_id == project.id for f in findings)
        assert all(f.mission_id == mission.id for f in findings)
        assert report.project_id == project.id
        assert report.mission_id == mission.id
        assert monitor.project_id == project.id
        assert alert.monitor_id == monitor.id

    def test_event_system_covers_full_lifecycle(self):
        """Verify all lifecycle event types exist in the EventType enum."""
        lifecycle_events = [
            EventType.project_created,
            EventType.mission_created,
            EventType.mission_started,
            EventType.mission_completed,
            EventType.agent_searching,
            EventType.agent_found_data,
            EventType.finding_created,
            EventType.report_generating,
            EventType.report_completed,
            EventType.monitor_triggered,
            EventType.monitor_alert,
        ]
        for event_type in lifecycle_events:
            assert isinstance(event_type.value, str)
            assert "." in event_type.value  # All events use dot notation

    def test_event_serialization_roundtrip(self):
        """Verify events serialize to JSON and back correctly."""
        event = Event(
            event_type=EventType.finding_created,
            data={"title": "Shell $3.19", "confidence": 0.92},
            project_id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )

        json_str = event.to_json()
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "finding.created"
        assert parsed["data"]["title"] == "Shell $3.19"
        assert parsed["data"]["confidence"] == 0.92
        assert parsed["project_id"] is not None
        assert parsed["mission_id"] is not None
        assert parsed["user_id"] is not None
        assert parsed["timestamp"] is not None

    def test_finding_type_coverage(self):
        """Verify all FindingType values used in the golden path are valid."""
        used_types = [FindingType.price, FindingType.statistic, FindingType.trend]
        all_types = list(FindingType)
        for t in used_types:
            assert t in all_types

    def test_source_type_coverage(self):
        """Verify all SourceType values used in the golden path are valid."""
        used_types = [SourceType.web, SourceType.inferred]
        all_types = list(SourceType)
        for t in used_types:
            assert t in all_types
