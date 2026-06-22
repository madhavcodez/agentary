"""Tests for the 3 onboarding endpoints:
1. POST /api/projects/{project_id}/generate-questions
2. POST /api/projects/{project_id}/configure-and-start
3. POST /api/missions/{mission_id}/synthesize-report
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.finding import Finding, FindingType, SourceType
from app.models.mission import Mission, MissionStatus
from app.models.project import Project, ProjectStatus
from app.models.user import User

# ── Helpers ────────────────────────────────────────────────────────────


def _get_dev_user(db) -> User:
    """Fetch the dev user that the app auto-creates in dev mode."""
    user = db.query(User).filter(User.email == "dev@agentary.local").first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email="dev@agentary.local",
            name="Dev User",
            password_hash="dev-no-login",
            is_active=True,
        )
        db.add(user)
        db.flush()
    return user


def _create_project(db, user_id: uuid.UUID, **overrides) -> Project:
    defaults = {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "name": "Test Project",
        "status": ProjectStatus.active,
    }
    defaults.update(overrides)
    project = Project(**defaults)
    db.add(project)
    db.flush()
    return project


def _create_mission(db, project: Project, user_id: uuid.UUID, **overrides) -> Mission:
    defaults = {
        "id": uuid.uuid4(),
        "project_id": project.id,
        "user_id": user_id,
        "name": "Test Mission",
        "status": MissionStatus.draft,
        "mission_type": "research",
    }
    defaults.update(overrides)
    mission = Mission(**defaults)
    db.add(mission)
    db.flush()
    return mission


def _create_finding(db, project: Project, mission: Mission, **overrides) -> Finding:
    defaults = {
        "id": uuid.uuid4(),
        "project_id": project.id,
        "mission_id": mission.id,
        "finding_type": FindingType.fact,
        "title": "Test Finding",
        "content": "Some research content here.",
        "source_type": SourceType.web,
        "source_url": "https://example.com",
        "source_name": "Example",
        "confidence": 0.85,
        "verified": False,
        "tags": ["test"],
    }
    defaults.update(overrides)
    finding = Finding(**defaults)
    db.add(finding)
    db.flush()
    return finding


# ═══════════════════════════════════════════════════════════════════════
# 1. POST /api/projects/{project_id}/generate-questions
# ═══════════════════════════════════════════════════════════════════════


class TestGenerateQuestions:
    """Tests for POST /api/projects/{project_id}/generate-questions."""

    @patch("app.services.gemini.generate_structured", new_callable=AsyncMock)
    def test_success_returns_questions(self, mock_gen, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        mock_gen.return_value = {
            "questions": [
                {
                    "id": "q1",
                    "question": "What market segment are you targeting?",
                    "type": "text",
                    "options": None,
                    "placeholder": "e.g. B2B SaaS",
                },
                {
                    "id": "q2",
                    "question": "What geographic region?",
                    "type": "select",
                    "options": ["US", "Europe", "Asia"],
                    "placeholder": "Select a region",
                },
            ],
        }

        resp = client.post(
            f"/api/projects/{project.id}/generate-questions",
            json={"title": "Market Research", "project_type": "market_research"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "questions" in data
        assert len(data["questions"]) == 2
        assert data["questions"][0]["id"] == "q1"
        assert data["questions"][0]["type"] == "text"
        assert data["questions"][1]["type"] == "select"
        assert data["questions"][1]["options"] == ["US", "Europe", "Asia"]

    def test_404_when_project_not_found(self, client, db):
        fake_id = uuid.uuid4()
        resp = client.post(
            f"/api/projects/{fake_id}/generate-questions",
            json={"title": "Test", "project_type": "market_research"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_validation_empty_title(self, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        resp = client.post(
            f"/api/projects/{project.id}/generate-questions",
            json={"title": "", "project_type": "market_research"},
        )
        assert resp.status_code == 422

    def test_validation_title_too_long(self, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        long_title = "x" * 501
        resp = client.post(
            f"/api/projects/{project.id}/generate-questions",
            json={"title": long_title, "project_type": "market_research"},
        )
        assert resp.status_code == 422

    @patch("app.services.gemini.generate_structured", new_callable=AsyncMock)
    def test_gemini_failure_returns_502(self, mock_gen, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        mock_gen.side_effect = Exception("Gemini API timeout")

        resp = client.post(
            f"/api/projects/{project.id}/generate-questions",
            json={"title": "Market Research", "project_type": "market_research"},
        )
        assert resp.status_code == 502
        assert "failed" in resp.json()["detail"].lower()

    @patch("app.services.gemini.generate_structured", new_callable=AsyncMock)
    def test_gemini_returns_empty_questions_502(self, mock_gen, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        mock_gen.return_value = {"questions": []}

        resp = client.post(
            f"/api/projects/{project.id}/generate-questions",
            json={"title": "Market Research", "project_type": "market_research"},
        )
        assert resp.status_code == 502
        assert "no questions" in resp.json()["detail"].lower()

    @patch("app.services.gemini.generate_structured", new_callable=AsyncMock)
    def test_questions_get_default_ids(self, mock_gen, client, db):
        """Questions missing 'id' should get auto-generated ids like q1, q2."""
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        mock_gen.return_value = {
            "questions": [
                {"question": "First question?", "type": "text"},
                {"question": "Second question?", "type": "text"},
            ],
        }

        resp = client.post(
            f"/api/projects/{project.id}/generate-questions",
            json={"title": "Test", "project_type": "custom"},
        )

        assert resp.status_code == 200
        questions = resp.json()["questions"]
        assert questions[0]["id"] == "q1"
        assert questions[1]["id"] == "q2"


# ═══════════════════════════════════════════════════════════════════════
# 2. POST /api/projects/{project_id}/configure-and-start
# ═══════════════════════════════════════════════════════════════════════


class TestConfigureAndStart:
    """Tests for POST /api/projects/{project_id}/configure-and-start."""

    @patch("app.services.crews.crew_service.start_crew_run", new_callable=AsyncMock)
    @patch("app.services.crews.crew_service.assemble_crew", new_callable=AsyncMock)
    @patch("app.services.gemini.generate_text", new_callable=AsyncMock)
    def test_success_creates_mission(
        self, mock_gen_text, mock_assemble, mock_start_run, client, db
    ):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        mock_gen_text.return_value = (
            "This research project focuses on the Austin TX housing market, "
            "targeting the 78704 zip code for median price trends."
        )

        # Mock crew assembly and run
        mock_crew = MagicMock()
        mock_crew.id = uuid.uuid4()
        mock_assemble.return_value = mock_crew

        mock_run = MagicMock()
        mock_run.id = uuid.uuid4()
        mock_start_run.return_value = mock_run

        resp = client.post(
            f"/api/projects/{project.id}/configure-and-start",
            json={
                "project_title": "Austin Housing Research",
                "answers": {
                    "What area?": "Austin TX 78704",
                    "What data?": "Median home prices",
                },
            },
        )

        assert resp.status_code == 200
        data = resp.json()

        # Verify project fields
        assert data["project"]["id"] == str(project.id)
        assert data["project"]["domain_context"] is not None
        assert len(data["project"]["domain_context"]) > 0

        # Verify mission fields
        assert "mission" in data
        assert data["mission"]["name"] == "Research: Austin Housing Research"
        assert data["mission"]["status"] == "draft"

    def test_404_when_project_not_found(self, client, db):
        fake_id = uuid.uuid4()
        resp = client.post(
            f"/api/projects/{fake_id}/configure-and-start",
            json={
                "project_title": "Test",
                "answers": {"q1": "answer1"},
            },
        )
        assert resp.status_code == 404

    def test_validation_too_many_answers(self, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        # 21 answers should exceed the max of 20
        answers = {f"q{i}": f"answer {i}" for i in range(21)}
        resp = client.post(
            f"/api/projects/{project.id}/configure-and-start",
            json={"project_title": "Test", "answers": answers},
        )
        assert resp.status_code == 422

    def test_validation_answer_too_long(self, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        resp = client.post(
            f"/api/projects/{project.id}/configure-and-start",
            json={
                "project_title": "Test",
                "answers": {"q1": "x" * 2001},
            },
        )
        assert resp.status_code == 422

    @patch("app.services.crews.crew_service.start_crew_run", new_callable=AsyncMock)
    @patch("app.services.crews.crew_service.assemble_crew", new_callable=AsyncMock)
    @patch("app.services.gemini.generate_text", new_callable=AsyncMock)
    def test_domain_context_updated_on_project(
        self, mock_gen_text, mock_assemble, mock_start_run, client, db
    ):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)
        assert project.domain_context is None

        expected_context = "Focused research on competitive landscape in fintech."
        mock_gen_text.return_value = expected_context

        mock_crew = MagicMock()
        mock_crew.id = uuid.uuid4()
        mock_assemble.return_value = mock_crew

        mock_run = MagicMock()
        mock_run.id = uuid.uuid4()
        mock_start_run.return_value = mock_run

        resp = client.post(
            f"/api/projects/{project.id}/configure-and-start",
            json={
                "project_title": "Fintech Competitive Analysis",
                "answers": {"q1": "Fintech startups"},
            },
        )

        assert resp.status_code == 200
        assert resp.json()["project"]["domain_context"] == expected_context.strip()

    @patch("app.services.crews.crew_service.start_crew_run", new_callable=AsyncMock)
    @patch("app.services.crews.crew_service.assemble_crew", new_callable=AsyncMock)
    @patch("app.services.gemini.generate_text", new_callable=AsyncMock)
    def test_gemini_failure_falls_back_to_raw_answers(
        self, mock_gen_text, mock_assemble, mock_start_run, client, db
    ):
        """When Gemini fails, domain_context should fall back to raw Q&A text."""
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        mock_gen_text.side_effect = Exception("Gemini down")

        mock_crew = MagicMock()
        mock_crew.id = uuid.uuid4()
        mock_assemble.return_value = mock_crew

        mock_run = MagicMock()
        mock_run.id = uuid.uuid4()
        mock_start_run.return_value = mock_run

        resp = client.post(
            f"/api/projects/{project.id}/configure-and-start",
            json={
                "project_title": "Fallback Test",
                "answers": {"What area?": "Austin TX"},
            },
        )

        assert resp.status_code == 200
        ctx = resp.json()["project"]["domain_context"]
        # Fallback should contain the raw answers
        assert "Austin TX" in ctx
        assert "Fallback Test" in ctx

    @patch("app.services.crews.crew_service.start_crew_run", new_callable=AsyncMock)
    @patch("app.services.crews.crew_service.assemble_crew", new_callable=AsyncMock)
    @patch("app.services.gemini.generate_text", new_callable=AsyncMock)
    def test_mission_returned_in_response(
        self, mock_gen_text, mock_assemble, mock_start_run, client, db
    ):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        mock_gen_text.return_value = "Domain context summary."

        mock_crew = MagicMock()
        mock_crew.id = uuid.uuid4()
        mock_assemble.return_value = mock_crew

        mock_run = MagicMock()
        mock_run.id = uuid.uuid4()
        mock_start_run.return_value = mock_run

        resp = client.post(
            f"/api/projects/{project.id}/configure-and-start",
            json={
                "project_title": "Mission Test",
                "answers": {"q1": "a1"},
            },
        )

        assert resp.status_code == 200
        mission_data = resp.json()["mission"]
        assert "id" in mission_data
        assert mission_data["name"] == "Research: Mission Test"
        assert mission_data["objective"] is not None
        assert mission_data["created_at"] is not None

    def test_validation_empty_project_title(self, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)

        resp = client.post(
            f"/api/projects/{project.id}/configure-and-start",
            json={
                "project_title": "",
                "answers": {"q1": "a1"},
            },
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════
# 3. POST /api/missions/{mission_id}/synthesize-report
# ═══════════════════════════════════════════════════════════════════════


class TestSynthesizeReport:
    """Tests for POST /api/missions/{mission_id}/synthesize-report."""

    @patch("app.services.gemini.generate_structured", new_callable=AsyncMock)
    def test_success_creates_report(self, mock_gen, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)
        mission = _create_mission(
            db,
            project,
            user.id,
            name="Austin Housing Research",
            objective="Find median home prices in Austin TX 78704",
        )
        _create_finding(db, project, mission, title="Median Price is $625K")
        _create_finding(
            db,
            project,
            mission,
            title="Prices rose 12% YoY",
            finding_type=FindingType.statistic,
            confidence=0.9,
        )

        mock_gen.return_value = {
            "title": "Austin Housing Market Report",
            "executive_summary": "The Austin TX 78704 housing market shows strong growth.",
            "sections": [
                {"title": "Pricing Overview", "content_md": "## Pricing\nMedian: $625K"},
                {"title": "Trends", "content_md": "## Trends\n12% YoY increase"},
            ],
            "methodology": "Web scraping and data analysis of public listings.",
            "content_markdown": "# Austin Housing Market\n\nMedian: $625K\n\n12% YoY increase",
        }

        resp = client.post(f"/api/missions/{mission.id}/synthesize-report")

        assert resp.status_code == 200
        data = resp.json()
        report = data["report"]

        assert report["title"] == "Austin Housing Market Report"
        assert report["status"] == "ready"
        assert "strong growth" in report["executive_summary"]
        assert len(report["sections"]) == 2
        assert report["sections"][0]["title"] == "Pricing Overview"
        assert report["methodology"] is not None
        assert report["content_markdown"] is not None
        assert report["sources"] is not None
        assert report["created_at"] is not None

    def test_404_when_mission_not_found(self, client, db):
        fake_id = uuid.uuid4()
        resp = client.post(f"/api/missions/{fake_id}/synthesize-report")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_400_when_no_findings(self, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)
        mission = _create_mission(db, project, user.id)
        # No findings created

        resp = client.post(f"/api/missions/{mission.id}/synthesize-report")
        assert resp.status_code == 400
        assert "no findings" in resp.json()["detail"].lower()

    @patch("app.services.gemini.generate_structured", new_callable=AsyncMock)
    def test_gemini_failure_returns_502(self, mock_gen, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)
        mission = _create_mission(db, project, user.id)
        _create_finding(db, project, mission)

        mock_gen.side_effect = Exception("Gemini API error")

        resp = client.post(f"/api/missions/{mission.id}/synthesize-report")
        assert resp.status_code == 502
        assert "failed" in resp.json()["detail"].lower()

    @patch("app.services.gemini.generate_structured", new_callable=AsyncMock)
    def test_report_has_correct_sources(self, mock_gen, client, db):
        user = _get_dev_user(db)
        project = _create_project(db, user.id)
        mission = _create_mission(db, project, user.id)
        _create_finding(
            db,
            project,
            mission,
            source_name="Zillow",
            source_url="https://zillow.com/78704",
            source_type=SourceType.web,
        )
        _create_finding(
            db,
            project,
            mission,
            title="Another Finding",
            source_name="Redfin",
            source_url="https://redfin.com/78704",
            source_type=SourceType.web,
        )

        mock_gen.return_value = {
            "title": "Report",
            "executive_summary": "Summary",
            "sections": [],
            "methodology": "Method",
            "content_markdown": "# Report",
        }

        resp = client.post(f"/api/missions/{mission.id}/synthesize-report")

        assert resp.status_code == 200
        sources = resp.json()["report"]["sources"]
        source_names = [s["name"] for s in sources]
        assert "Zillow" in source_names
        assert "Redfin" in source_names

    @patch("app.services.gemini.generate_structured", new_callable=AsyncMock)
    def test_report_deduplicates_sources(self, mock_gen, client, db):
        """Findings with the same source URL should produce only one source entry."""
        user = _get_dev_user(db)
        project = _create_project(db, user.id)
        mission = _create_mission(db, project, user.id)

        for i in range(3):
            _create_finding(
                db,
                project,
                mission,
                title=f"Finding {i}",
                source_name="Zillow",
                source_url="https://zillow.com/78704",
                source_type=SourceType.web,
            )

        mock_gen.return_value = {
            "title": "Report",
            "executive_summary": "Summary",
            "sections": [],
            "methodology": "Method",
            "content_markdown": "# Report",
        }

        resp = client.post(f"/api/missions/{mission.id}/synthesize-report")

        assert resp.status_code == 200
        sources = resp.json()["report"]["sources"]
        assert len(sources) == 1
        assert sources[0]["name"] == "Zillow"

    @patch("app.services.gemini.generate_structured", new_callable=AsyncMock)
    def test_report_sections_have_order(self, mock_gen, client, db):
        """Each section should have an 'order' field matching its index."""
        user = _get_dev_user(db)
        project = _create_project(db, user.id)
        mission = _create_mission(db, project, user.id)
        _create_finding(db, project, mission)

        mock_gen.return_value = {
            "title": "Report",
            "executive_summary": "Summary",
            "sections": [
                {"title": "Section A", "content_md": "Content A"},
                {"title": "Section B", "content_md": "Content B"},
                {"title": "Section C", "content_md": "Content C"},
            ],
            "methodology": "Method",
            "content_markdown": "# Report",
        }

        resp = client.post(f"/api/missions/{mission.id}/synthesize-report")

        assert resp.status_code == 200
        sections = resp.json()["report"]["sections"]
        assert len(sections) == 3
        for i, section in enumerate(sections):
            assert section["order"] == i
            assert section["title"] == f"Section {'ABC'[i]}"
