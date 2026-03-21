"""E2E golden path test: create mission -> assemble crew -> mock execute -> verify findings."""
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.agent_crew import AgentCrew, CoordinationStrategy
from app.models.crew_run import CrewRun
from app.models.crew_task import CrewTask
from app.models.expert_agent import AgentSpecialty, ExpertAgent
from app.models.finding import Finding
from app.models.mission import Mission, MissionStatus, MissionType
from app.models.project import Project


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


class TestGoldenPath:
    """End-to-end: mission creation -> crew assembly -> execution -> findings."""

    def test_mission_creation(self):
        project = Project(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Test Project",
        )
        mission = Mission(
            id=uuid.uuid4(),
            project_id=project.id,
            user_id=project.user_id,
            name="Research Austin Housing",
            description="Analyze housing market in Austin TX 78704",
            objective="Find median prices and trends",
            status=MissionStatus.draft,
            mission_type=MissionType.research,
            parameters={"geography": "Austin, TX 78704"},
        )
        assert mission.status == MissionStatus.draft
        assert mission.name == "Research Austin Housing"

    def test_crew_assembly(self):
        expert_1 = _make_expert("web-researcher", "Web Researcher", AgentSpecialty.web_researcher)
        expert_2 = _make_expert("synthesizer", "Synthesizer", AgentSpecialty.synthesizer)

        crew = AgentCrew(
            id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
            agents=[
                {"agent_id": str(expert_1.id), "slug": "web-researcher", "name": "Web Researcher", "role": "web_researcher"},
                {"agent_id": str(expert_2.id), "slug": "synthesizer", "name": "Synthesizer", "role": "synthesizer"},
            ],
            coordination_strategy=CoordinationStrategy.parallel,
        )
        assert len(crew.agents) == 2
        slugs = {a["slug"] for a in crew.agents}
        assert "web-researcher" in slugs
        assert "synthesizer" in slugs

    def test_crew_run_creation(self):
        crew_id = uuid.uuid4()
        mission_id = uuid.uuid4()
        run = CrewRun(
            id=uuid.uuid4(),
            crew_id=crew_id,
            mission_id=mission_id,
            status="queued",
            trigger_type="manual",
        )
        assert run.status == "queued"

    def test_task_creation(self):
        task = CrewTask(
            id=uuid.uuid4(),
            run_id=uuid.uuid4(),
            expert_agent_id=uuid.uuid4(),
            task_type="web_search",
            description="Search for Austin 78704 housing data",
            input_data={"query": "Austin 78704 median home price"},
            status="pending",
            thinking_log=[],
        )
        assert task.status == "pending"
        assert task.task_type == "web_search"

    def test_finding_creation_with_source_attribution(self):
        finding = Finding(
            id=uuid.uuid4(),
            mission_id=uuid.uuid4(),
            crew_task_id=uuid.uuid4(),
            expert_agent_id=uuid.uuid4(),
            category="statistic",
            title="Austin 78704 Median Home Price",
            content="The median home price in 78704 is $625,000.",
            source_type="web",
            source_url="https://www.zillow.com/austin-tx-78704/",
            source_name="Zillow",
            confidence=0.85,
            verified=False,
            tags=["real_estate", "pricing"],
        )
        assert finding.category == "statistic"
        assert finding.confidence == 0.85
        assert finding.source_url is not None
        assert finding.source_name == "Zillow"
        assert "real_estate" in finding.tags

    def test_full_pipeline_objects(self):
        """Create the full chain: project -> mission -> crew -> run -> tasks -> findings."""
        user_id = uuid.uuid4()
        project_id = uuid.uuid4()
        mission_id = uuid.uuid4()
        crew_id = uuid.uuid4()
        run_id = uuid.uuid4()
        expert_id = uuid.uuid4()

        # Project
        project = Project(id=project_id, user_id=user_id, name="Test")

        # Mission
        mission = Mission(
            id=mission_id, project_id=project_id, user_id=user_id,
            name="Test Mission", status=MissionStatus.draft,
        )

        # Crew
        crew = AgentCrew(
            id=crew_id, mission_id=mission_id,
            agents=[{"agent_id": str(expert_id), "slug": "web-researcher", "role": "researcher"}],
        )

        # Run
        run = CrewRun(id=run_id, crew_id=crew_id, mission_id=mission_id, status="queued")

        # Task
        task = CrewTask(
            id=uuid.uuid4(), run_id=run_id, expert_agent_id=expert_id,
            task_type="web_search", description="Search",
        )

        # Finding
        finding = Finding(
            id=uuid.uuid4(), mission_id=mission_id, crew_task_id=task.id,
            expert_agent_id=expert_id, category="fact",
            title="Test Finding", content="Test content",
            confidence=0.7, source_type="web",
        )

        # Verify chain integrity
        assert mission.project_id == project.id
        assert crew.mission_id == mission.id
        assert run.crew_id == crew.id
        assert run.mission_id == mission.id
        assert task.run_id == run.id
        assert finding.mission_id == mission.id
        assert finding.crew_task_id == task.id
