"""Tests for monitor service core logic."""

from unittest.mock import MagicMock
from uuid import uuid4

from app.services.change_detector import ChangeResult
from app.services.monitor_service import (
    _create_alert,
    _detect_changes,
    _extract_value,
)


class TestExtractValue:
    def test_simple_field(self):
        assert _extract_value({"price": 100}, "price") == 100.0

    def test_nested_field(self):
        assert _extract_value({"data": {"price": 42.5}}, "data.price") == 42.5

    def test_missing_field(self):
        assert _extract_value({"foo": "bar"}, "price") is None

    def test_non_numeric(self):
        assert _extract_value({"price": "N/A"}, "price") is None


class TestDetectChanges:
    def _make_monitor(self, monitor_type, last_snapshot=None, check_config=None):
        m = MagicMock()
        m.monitor_type = monitor_type
        m.last_snapshot = last_snapshot
        m.check_config = check_config or {}
        return m

    def test_initial_snapshot(self):
        m = self._make_monitor("web_content", last_snapshot=None)
        result = _detect_changes(m, {"content": "hello"})
        assert not result.changed
        assert "Initial" in result.summary

    def test_web_content_no_change(self):
        m = self._make_monitor("web_content", last_snapshot={"content": "same"})
        result = _detect_changes(m, {"content": "same"})
        assert not result.changed

    def test_web_content_change(self):
        m = self._make_monitor("web_content", last_snapshot={"content": "old"})
        result = _detect_changes(m, {"content": "new"})
        assert result.changed

    def test_price_tracker(self):
        m = self._make_monitor(
            "price_tracker",
            last_snapshot={"price": 100},
            check_config={"value_field": "price", "threshold": 5},
        )
        result = _detect_changes(m, {"price": 120})
        assert result.changed
        assert "increased" in result.summary

    def test_price_tracker_within_threshold(self):
        m = self._make_monitor(
            "price_tracker",
            last_snapshot={"price": 100},
            check_config={"value_field": "price", "threshold": 25},
        )
        result = _detect_changes(m, {"price": 120})
        assert not result.changed

    def test_listing_watcher_new_items(self):
        m = self._make_monitor(
            "listing_watcher",
            last_snapshot={"data": [{"id": "1"}]},
        )
        result = _detect_changes(m, {"data": [{"id": "1"}, {"id": "2"}]})
        assert result.changed
        assert "1 new" in result.summary


class TestCreateAlert:
    def test_creates_alert(self):
        db = MagicMock()
        monitor = MagicMock()
        monitor.id = uuid4()
        monitor.project_id = None
        monitor.name = "Test Monitor"

        changes = ChangeResult(
            changed=True,
            change_type="text",
            summary="3 lines added",
            details={"added_lines": 3},
        )

        alert = _create_alert(db, monitor, changes)
        assert alert.title == "Test Monitor: 3 lines added"
        assert alert.alert_type == "change_detected"
        db.add.assert_called_once()
        db.flush.assert_called_once()
