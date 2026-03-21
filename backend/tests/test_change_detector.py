"""Tests for the change detector utility."""

from app.services.change_detector import (
    detect_new_items,
    detect_removed_items,
    detect_text_change,
    detect_value_change,
)


class TestDetectTextChange:
    def test_no_change(self):
        result = detect_text_change("hello world", "hello world")
        assert not result.changed
        assert result.change_type == "text"

    def test_change_detected(self):
        result = detect_text_change("line one\nline two", "line one\nline three")
        assert result.changed
        assert result.change_type == "text"
        assert "1 lines added" in result.summary
        assert "1 lines removed" in result.summary

    def test_none_to_text(self):
        result = detect_text_change(None, "new content")
        assert result.changed

    def test_text_to_none(self):
        result = detect_text_change("old content", None)
        assert result.changed

    def test_both_none(self):
        result = detect_text_change(None, None)
        assert not result.changed


class TestDetectValueChange:
    def test_no_change(self):
        result = detect_value_change(100, 100)
        assert not result.changed

    def test_increase(self):
        result = detect_value_change(100, 150)
        assert result.changed
        assert "increased" in result.summary
        assert result.details["difference"] == 50

    def test_decrease(self):
        result = detect_value_change(200, 100)
        assert result.changed
        assert "decreased" in result.summary

    def test_within_threshold(self):
        result = detect_value_change(100, 102, threshold=5)
        assert not result.changed

    def test_exceeds_threshold(self):
        result = detect_value_change(100, 110, threshold=5)
        assert result.changed

    def test_none_values(self):
        result = detect_value_change(None, 100)
        assert result.changed

    def test_both_none(self):
        result = detect_value_change(None, None)
        assert not result.changed


class TestDetectNewItems:
    def test_no_new_items(self):
        old = [{"id": "1"}, {"id": "2"}]
        new = [{"id": "1"}, {"id": "2"}]
        result = detect_new_items(old, new)
        assert not result.changed

    def test_new_items_found(self):
        old = [{"id": "1"}]
        new = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        result = detect_new_items(old, new)
        assert result.changed
        assert result.details["count"] == 2

    def test_empty_old_list(self):
        result = detect_new_items(None, [{"id": "1"}])
        assert result.changed
        assert result.details["count"] == 1

    def test_empty_new_list(self):
        result = detect_new_items([{"id": "1"}], None)
        assert not result.changed

    def test_custom_key(self):
        old = [{"url": "a.com"}]
        new = [{"url": "a.com"}, {"url": "b.com"}]
        result = detect_new_items(old, new, key="url")
        assert result.changed
        assert result.details["count"] == 1


class TestDetectRemovedItems:
    def test_no_removed(self):
        old = [{"id": "1"}]
        new = [{"id": "1"}, {"id": "2"}]
        result = detect_removed_items(old, new)
        assert not result.changed

    def test_items_removed(self):
        old = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        new = [{"id": "1"}]
        result = detect_removed_items(old, new)
        assert result.changed
        assert result.details["count"] == 2
