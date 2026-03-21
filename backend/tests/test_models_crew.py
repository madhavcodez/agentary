"""Tests for all research engine models."""
import uuid
from datetime import datetime, timezone

import pytest

from app.models.project import Project, ProjectStatus
from app.models.expert_agent import ExpertAgent, AgentSpecialty
from app.models.mission import Mission, MissionStatus, MissionType
from app.models.agent_crew import AgentCrew, CoordinationStrategy, AgentActivity, ActivityType
from app.models.mission_run import MissionRun, MissionTask, RunStatus, TriggerType
from app.models.crew_task import CrewTask, CrewTaskStatus
from app.models.finding import Finding
from app.models.report import Report


class TestProjectModel:
    def test_create_project(self):
        project = Project(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Real Estate Research",
            description="Market analysis for Austin TX",
            status=ProjectStatus.active,
        )
        assert project.name == "Real Estate Research"
        assert project.status == ProjectStatus.active


class TestExpertAgentModel:
    def test_create_expert_agent(self):
        agent = ExpertAgent(
            id=uuid.uuid4(),
            slug="web-researcher",
            name="Web Researcher",
            description="Searches the web",
            specialty=AgentSpecialty.web_researcher,
            system_prompt="You are a web researcher...",
            tools=["gemini_search", "exa_search"],
            model_config_json={"model": "gemini-2.5-flash", "temperature": 0.3},
            icon="\U0001f50d",
            color="#3B82F6",
            is_system=True,
            is_active=True,
        )
        assert agent.slug == "web-researcher"
        assert agent.specialty == AgentSpecialty.web_researcher
        assert agent.is_system is True

    def test_all_specialties_exist(self):
        expected = {
            "web_researcher", "data_extractor", "voice_caller",
            "market_analyst", "financial_analyst", "real_estate_expert",
            "competitive_intel", "due_diligence", "synthesizer",
            "local_business_intel",
        }
        actual = {s.value for s in AgentSpecialty}
        assert expected == actual


class TestMissionModel:
    def test_create_mission(self):
        mission = Mission(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Research Austin 78704",
            description="Housing market analysis",
            objective="Understand price trends and inventory",
            status=MissionStatus.draft,
            mission_type=MissionType.research,
            parameters={"geography": "Austin, TX 78704"},
        )
        assert mission.name == "Research Austin 78704"
        assert mission.status == MissionStatus.draft
        assert mission.parameters["geography"] == "Austin, TX 78704"

    def test_all_statuses_exist(self):
        expected = {"draft", "queued", "running", "paused", "completed", "failed"}
        actual = {s.value for s in MissionStatus}
        assert expected == actual


class TestAgentCrewModel:
    def test_create_crew(self):
        crew = AgentCrew(
            id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
            agents=[
                {"agent_id": str(uuid.uuid4()), "slug": "web-researcher", "role": "researcher"},
                {"agent_id": str(uuid.uuid4()), "slug": "synthesizer", "role": "synthesizer"},
            ],
            coordination_strategy=CoordinationStrategy.parallel,
        )
        assert len(crew.agents) == 2
        assert crew.coordination_strategy == CoordinationStrategy.parallel


class TestMissionRunModel:
    def test_create_run(self):
        run = MissionRun(
            id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
            status=RunStatus.queued,
            trigger_type=TriggerType.manual,
            metrics={},
        )
        assert run.status == RunStatus.queued
        assert run.trigger_type == TriggerType.manual


class TestCrewTaskModel:
    def test_create_task(self):
        task = CrewTask(
            id=uuid.uuid4(),
            mission_run_id=uuid.uuid4(),
            expert_agent_id=uuid.uuid4(),
            task_type="web_search",
            description="Search for Austin housing data",
            input_data={"query": "Austin 78704 median home price"},
            status=CrewTaskStatus.pending,
            thinking_log=[],
        )
        assert task.task_type == "web_search"
        assert task.status == CrewTaskStatus.pending
        assert isinstance(task.thinking_log, list)

    def test_thinking_log_structure(self):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "thought": "Searching for pricing data",
            "action": "searching",
            "tool": "gemini_search",
            "result_preview": "Found 47 results...",
        }
        task = CrewTask(
            id=uuid.uuid4(),
            mission_run_id=uuid.uuid4(),
            expert_agent_id=uuid.uuid4(),
            task_type="web_search",
            description="test",
            thinking_log=[log_entry],
        )
        assert len(task.thinking_log) == 1
        assert task.thinking_log[0]["tool"] == "gemini_search"


class TestFindingModel:
    def test_create_finding(self):
        from app.models.finding import FindingType, SourceType as FSourceType
        finding = Finding(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
            finding_type=FindingType.statistic,
            title="Median Home Price Austin 78704",
            content="The median home price in Austin 78704 is $625,000 as of March 2026.",
            source_type=FSourceType.web,
            source_url="https://www.zillow.com/austin-tx-78704/",
            source_name="Zillow",
            confidence=0.85,
            tags=["real_estate", "pricing", "austin"],
        )
        assert finding.title == "Median Home Price Austin 78704"
        assert finding.confidence == 0.85
        assert finding.source_type == FSourceType.web
        assert "real_estate" in finding.tags


class TestReportModel:
    def test_create_report(self):
        result = Report(
            id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            title="Austin 78704 Housing Market Report",
            report_type="research_report",
            status="generating",
            executive_summary="Comprehensive analysis of the housing market...",
            sections=[
                {"title": "Executive Summary", "content": "...", "finding_ids": []},
                {"title": "Price Trends", "content": "...", "chart_configs": []},
            ],
            methodology="Multi-expert parallel research with web, data, and synthesis phases",
        )
        assert result.title == "Austin 78704 Housing Market Report"
        assert len(result.sections) == 2
        assert result.report_type == "research_report"


class TestAgentActivityModel:
    def test_create_activity(self):
        activity = AgentActivity(
            id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
            activity_type=ActivityType.searching,
            content="Searching for Austin housing data...",
            metadata_json={"tool": "gemini_search", "query": "Austin 78704"},
            confidence=0.8,
        )
        assert activity.activity_type == ActivityType.searching
        assert activity.metadata_json["tool"] == "gemini_search"
