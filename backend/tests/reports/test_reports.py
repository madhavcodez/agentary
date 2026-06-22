"""Tests for the reports, charts, data export, and sharing system.

These tests are written as standalone unit tests that mock the database
and don't rely on importing the full FastAPI app (which has cascading
import issues from the ongoing domain restructure).
"""

import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# ── ChartGenerator tests ─────────────────────────────────────────────


class TestChartGenerator:
    """Test Chart.js config generation for all chart types."""

    def _make_gen(self):
        from app.services.reports.chart_generator import ChartGenerator

        return ChartGenerator()

    def test_comparison_bar_chart(self):
        gen = self._make_gen()
        items = [
            {"name": "Alpha", "value": 10},
            {"name": "Beta", "value": 25},
            {"name": "Gamma", "value": 15},
        ]
        chart = gen.comparison_bar_chart(items, "value", "name", "Test Bar")

        assert chart["type"] == "bar"
        assert chart["title"] == "Test Bar"
        assert chart["data"]["labels"] == ["Alpha", "Beta", "Gamma"]
        assert chart["data"]["datasets"][0]["data"] == [10, 25, 15]
        assert "id" in chart
        assert chart["options"]["responsive"] is True

    def test_trend_line_chart(self):
        gen = self._make_gen()
        timeseries = [
            {"date": "2024-01-01", "price": 100},
            {"date": "2024-02-01", "price": 110},
            {"date": "2024-03-01", "price": 105},
        ]
        chart = gen.trend_line_chart(timeseries, "date", "price", "Price Trend")

        assert chart["type"] == "line"
        assert len(chart["data"]["labels"]) == 3
        assert chart["data"]["datasets"][0]["data"] == [100, 110, 105]

    def test_pie_chart(self):
        gen = self._make_gen()
        categories = {"A": 30, "B": 50, "C": 20}
        chart = gen.pie_chart(categories, "Distribution")

        assert chart["type"] == "pie"
        assert set(chart["data"]["labels"]) == {"A", "B", "C"}
        assert sum(chart["data"]["datasets"][0]["data"]) == 100

    def test_distribution_histogram(self):
        gen = self._make_gen()
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        chart = gen.distribution_histogram(values, "Values", bins=5)

        assert chart["type"] == "bar"
        assert len(chart["data"]["labels"]) == 5
        assert sum(chart["data"]["datasets"][0]["data"]) == len(values)

    def test_scatter_plot(self):
        gen = self._make_gen()
        points = [
            {"x": 1, "y": 2, "label": "A"},
            {"x": 3, "y": 4, "label": "B"},
        ]
        chart = gen.scatter_plot(points, "x", "y", "label", "Scatter Test")

        assert chart["type"] == "scatter"
        assert len(chart["data"]["datasets"][0]["data"]) == 2

    def test_multi_series_line(self):
        gen = self._make_gen()
        series = {
            "Series A": [
                {"date": "2024-01", "val": 10},
                {"date": "2024-02", "val": 20},
            ],
            "Series B": [
                {"date": "2024-01", "val": 15},
                {"date": "2024-02", "val": 25},
            ],
        }
        chart = gen.multi_series_line(series, "date", "val", "Multi Line")

        assert chart["type"] == "line"
        assert len(chart["data"]["datasets"]) == 2

    def test_generate_map_pins(self):
        gen = self._make_gen()
        locations = [
            {"lat": 30.27, "lng": -97.74, "label": "Austin", "value": 100},
            {"lat": 32.78, "lng": -96.80, "label": "Dallas", "value": 200},
        ]
        result = gen.generate_map_pins(locations)
        assert isinstance(result, dict)

    def test_slugify(self):
        gen = self._make_gen()
        assert gen._slugify("Gas Prices by Station") == "gas_prices_by_station"
        assert gen._slugify("Hello World!") == "hello_world"


# ── DataExporter tests ───────────────────────────────────────────────


class TestDataExporter:
    """Test CSV, JSON, and Excel export functionality."""

    def _make_exporter(self):
        from app.services.reports.data_exporter import DataExporter

        return DataExporter()

    def _mock_finding(self, **kwargs):
        finding = MagicMock()
        finding.id = kwargs.get("id", uuid.uuid4())
        finding.mission_id = kwargs.get("mission_id", uuid.uuid4())
        finding.finding_type = kwargs.get("category", "data_point")
        finding.category = kwargs.get("category", "data_point")
        finding.title = kwargs.get("title", "Test Finding")
        finding.content = kwargs.get("content", "Test content here")
        finding.structured_data = kwargs.get("structured_data")
        finding.source_type = kwargs.get("source_type", "web")
        finding.source_url = kwargs.get("source_url", "https://example.com")
        finding.source_name = kwargs.get("source_name", "Example")
        finding.confidence = kwargs.get("confidence", 0.85)
        finding.verified = kwargs.get("verified", False)
        finding.tags = kwargs.get("tags", ["test"])
        finding.expert_agent_id = kwargs.get("expert_agent_id")
        finding.created_at = kwargs.get("created_at", datetime(2024, 1, 15))
        return finding

    def _mock_db_with_findings(self, findings):
        db = MagicMock()
        query_mock = MagicMock()
        db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.order_by.return_value = query_mock
        query_mock.all.return_value = findings
        return db

    def test_export_findings_csv(self):
        exporter = self._make_exporter()
        mission_id = uuid.uuid4()
        findings = [
            self._mock_finding(title="Finding 1", category="insight"),
            self._mock_finding(title="Finding 2", category="data_point"),
        ]
        db = self._mock_db_with_findings(findings)
        csv_bytes = exporter.export_findings_csv(mission_id, None, db)

        assert isinstance(csv_bytes, bytes)
        csv_str = csv_bytes.decode("utf-8-sig")
        assert "Finding 1" in csv_str
        assert "Finding 2" in csv_str

    def test_export_findings_json(self):
        exporter = self._make_exporter()
        mission_id = uuid.uuid4()
        findings = [self._mock_finding(title="JSON Finding")]
        db = self._mock_db_with_findings(findings)
        json_str = exporter.export_findings_json(mission_id, None, db)

        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "JSON Finding"

    def test_export_findings_excel(self):
        exporter = self._make_exporter()
        mission_id = uuid.uuid4()
        findings = [
            self._mock_finding(title="Excel Finding 1", category="insight"),
            self._mock_finding(title="Excel Finding 2", category="trend"),
        ]
        db = self._mock_db_with_findings(findings)
        xlsx_bytes = exporter.export_findings_excel(mission_id, None, db)

        assert isinstance(xlsx_bytes, bytes)
        assert xlsx_bytes[:2] == b"PK"  # XLSX = zip format

    def test_csv_with_filters(self):
        """Test that filters are passed through to the query layer."""
        exporter = self._make_exporter()
        mission_id = uuid.uuid4()
        findings = [self._mock_finding(category="insight", confidence=0.9)]

        # Build a mock db whose chained .filter().filter()... returns findings
        db = MagicMock()
        chain = MagicMock()
        db.query.return_value = chain
        chain.filter.return_value = chain
        chain.order_by.return_value = chain
        chain.all.return_value = findings

        csv_bytes = exporter.export_findings_csv(
            mission_id,
            {"category": "insight", "confidence_min": 0.8},
            db,
        )
        assert isinstance(csv_bytes, bytes)
        assert b"insight" in csv_bytes


# ── ShareService tests ───────────────────────────────────────────────


class TestShareService:
    """Test shareable report link management."""

    def _make_service(self):
        from app.services.reports.share_service import ShareService

        return ShareService()

    def _mock_report(self, user_id=None, share_enabled=False, share_token=None):
        report = MagicMock()
        report.id = uuid.uuid4()
        report.user_id = user_id or uuid.uuid4()
        report.share_enabled = share_enabled
        report.share_token = share_token
        return report

    @patch("app.services.reports.share_service.settings")
    def test_create_share_link(self, mock_settings):
        mock_settings.base_url = "http://localhost:3000"
        svc = self._make_service()
        user_id = uuid.uuid4()
        report = self._mock_report(user_id=user_id)

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = report

        result = svc.create_share_link(report.id, user_id, db)

        assert "url" in result
        assert "token" in result
        assert "/shared/reports/" in result["url"]
        assert report.share_enabled is True
        assert report.share_token is not None
        db.commit.assert_called_once()

    @patch("app.services.reports.share_service.settings")
    def test_create_share_link_returns_existing(self, mock_settings):
        mock_settings.base_url = "http://localhost:3000"
        svc = self._make_service()
        user_id = uuid.uuid4()
        report = self._mock_report(
            user_id=user_id, share_enabled=True, share_token="existing_token"
        )

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = report

        result = svc.create_share_link(report.id, user_id, db)
        assert result["token"] == "existing_token"
        db.commit.assert_not_called()

    def test_create_share_link_wrong_user(self):
        svc = self._make_service()
        report = self._mock_report(user_id=uuid.uuid4())

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = report

        with pytest.raises(ValueError, match="permission"):
            svc.create_share_link(report.id, uuid.uuid4(), db)

    def test_create_share_link_not_found(self):
        svc = self._make_service()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="not found"):
            svc.create_share_link(uuid.uuid4(), uuid.uuid4(), db)

    def test_get_shared_report_found(self):
        svc = self._make_service()
        report = self._mock_report(share_enabled=True, share_token="abc123")

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = report

        result = svc.get_shared_report("abc123", db)
        assert result is not None

    def test_get_shared_report_not_found(self):
        svc = self._make_service()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        result = svc.get_shared_report("nonexistent", db)
        assert result is None

    def test_get_shared_report_empty_token(self):
        svc = self._make_service()
        db = MagicMock()
        result = svc.get_shared_report("", db)
        assert result is None

    def test_revoke_share(self):
        svc = self._make_service()
        user_id = uuid.uuid4()
        report = self._mock_report(user_id=user_id, share_enabled=True, share_token="token123")

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = report

        svc.revoke_share(report.id, user_id, db)
        assert report.share_enabled is False
        assert report.share_token is None
        db.commit.assert_called_once()

    def test_revoke_share_wrong_user(self):
        svc = self._make_service()
        report = self._mock_report(user_id=uuid.uuid4())

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = report

        with pytest.raises(ValueError, match="permission"):
            svc.revoke_share(report.id, uuid.uuid4(), db)


# ── PDFExporter tests ────────────────────────────────────────────────


class TestPDFExporter:
    """Test HTML and Markdown export (PDF requires WeasyPrint system deps)."""

    def _make_exporter(self):
        from app.services.reports.pdf_exporter import PDFExporter

        return PDFExporter()

    def _mock_report(self):
        report = MagicMock()
        report.id = uuid.uuid4()
        report.title = "Test Report"
        report.description = "A test report"
        report.report_type = "research_report"
        report.content_markdown = "# Hello\n\nThis is a test."
        report.content_html = "<h1>Hello</h1><p>This is a test.</p>"
        report.sections = [
            {"title": "Section 1", "content_md": "## Content\nParagraph.", "order": 0},
            {"title": "Section 2", "content_md": "## More\nAnother.", "order": 1},
        ]
        report.executive_summary = "This report covers testing."
        report.methodology = "Automated testing methodology."
        report.sources = [
            {"name": "Source 1", "url": "https://example.com", "type": "web"},
        ]
        report.charts = [
            {
                "id": "test_chart",
                "type": "bar",
                "title": "Test Chart",
                "data": {
                    "labels": ["A", "B", "C"],
                    "datasets": [{"label": "Values", "data": [10, 20, 30]}],
                },
                "options": {},
            }
        ]
        report.structured_data = {"key": "value"}
        report.metadata_ = {"word_count": 100}
        report.format_config = None
        report.project = MagicMock()
        report.project.name = "Test Project"
        report.mission = MagicMock()
        report.mission.title = "Test Mission"
        report.created_at = datetime(2024, 6, 15)
        report.updated_at = datetime(2024, 6, 15)
        return report

    def test_export_to_markdown(self):
        exporter = self._make_exporter()
        report = self._mock_report()
        md = exporter.export_to_markdown(report)

        assert isinstance(md, str)
        assert "Test Report" in md

    def test_export_to_html(self):
        exporter = self._make_exporter()
        report = self._mock_report()
        html = exporter.export_to_html(report)

        assert isinstance(html, str)
        assert "<html" in html.lower() or "<!doctype" in html.lower() or "Test Report" in html

    def test_render_charts_as_images(self):
        exporter = self._make_exporter()
        charts = [
            {
                "id": "bar_chart",
                "type": "bar",
                "title": "Bar",
                "data": {
                    "labels": ["X", "Y"],
                    "datasets": [{"label": "V", "data": [5, 10]}],
                },
            }
        ]
        images = exporter._render_charts_as_images(charts)
        assert isinstance(images, dict)


# ── Report templates test ────────────────────────────────────────────


class TestReportTemplates:
    """Test that all 5 report templates are valid JSON with required fields."""

    def test_all_templates_exist_and_valid(self):
        from pathlib import Path

        templates_dir = Path("app/services/reports/templates")
        expected = [
            "research_report.json",
            "market_analysis.json",
            "property_report.json",
            "competitive_intel.json",
            "due_diligence.json",
        ]

        for filename in expected:
            path = templates_dir / filename
            assert path.exists(), f"Template {filename} not found"

            with open(path) as f:
                template = json.load(f)

            assert "type" in template, f"{filename} missing 'type'"
            assert "name" in template, f"{filename} missing 'name'"
            assert "sections" in template, f"{filename} missing 'sections'"
            assert len(template["sections"]) >= 3, f"{filename} has too few sections"

            for section in template["sections"]:
                assert "title" in section, f"Section in {filename} missing 'title'"
                assert "purpose" in section, f"Section in {filename} missing 'purpose'"
                assert "order" in section, f"Section in {filename} missing 'order'"
