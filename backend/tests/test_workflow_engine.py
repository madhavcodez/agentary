"""Tests for the workflow engine — models, validation, executor, and node handlers."""

from __future__ import annotations

import asyncio

import pytest

from app.services.workflow.node_handlers import (
    execute_handler,
    handle_aggregate,
    handle_condition,
    handle_deduplicate,
    handle_export_data,
    handle_filter,
    handle_generate_chart,
    handle_manual_trigger,
    handle_merge,
    handle_sort,
    handle_transform,
)
from app.services.workflow.node_registry import (
    NODE_TYPES,
    get_all_node_types_summary,
    get_node_type,
    get_node_types_by_category,
    validate_node_config,
)
from app.services.workflow.service import validate_workflow

# ── Node Registry Tests ──────────────────────────────────────────────

class TestNodeRegistry:
    def test_all_27_node_types_registered(self):
        assert len(NODE_TYPES) == 27

    def test_get_node_type(self):
        info = get_node_type("web_search")
        assert info is not None
        assert info["category"] == "research"
        assert info["label"] == "Web Search"

    def test_get_node_type_unknown(self):
        assert get_node_type("unknown_type") is None

    def test_get_node_types_by_category(self):
        triggers = get_node_types_by_category("trigger")
        assert len(triggers) == 3
        assert "manual_trigger" in triggers
        assert "schedule_trigger" in triggers
        assert "webhook_trigger" in triggers

    def test_get_all_node_types_summary(self):
        summary = get_all_node_types_summary()
        assert len(summary) == 27
        assert all("type" in s for s in summary)
        assert all("category" in s for s in summary)

    def test_validate_node_config_valid(self):
        errors = validate_node_config("web_search", {"query_template": "test query"})
        assert errors == []

    def test_validate_node_config_missing_required(self):
        errors = validate_node_config("web_search", {})
        assert len(errors) == 1
        assert "query_template" in errors[0]

    def test_validate_node_config_unknown_type(self):
        errors = validate_node_config("unknown", {})
        assert len(errors) == 1
        assert "Unknown node type" in errors[0]

    def test_all_categories_present(self):
        categories = {info["category"] for info in NODE_TYPES.values()}
        assert categories == {"trigger", "research", "data", "analysis", "output", "control"}

    def test_each_node_has_required_fields(self):
        for name, info in NODE_TYPES.items():
            assert "category" in info, f"{name} missing category"
            assert "label" in info, f"{name} missing label"
            assert "description" in info, f"{name} missing description"
            assert "config_schema" in info, f"{name} missing config_schema"
            assert "inputs" in info, f"{name} missing inputs"
            assert "outputs" in info, f"{name} missing outputs"


# ── Workflow Validation Tests ────────────────────────────────────────

class TestWorkflowValidation:
    def test_validate_empty_workflow(self):
        errors = validate_workflow([], [])
        assert any("at least one node" in e for e in errors)

    def test_validate_valid_linear_workflow(self):
        nodes = [
            {"id": "n1", "type": "manual_trigger", "config": {}},
            {"id": "n2", "type": "web_search", "config": {"query_template": "test"}},
            {"id": "n3", "type": "generate_report", "config": {}},
        ]
        edges = [
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
        ]
        errors = validate_workflow(nodes, edges)
        assert errors == []

    def test_validate_cycle_detected(self):
        nodes = [
            {"id": "n1", "type": "manual_trigger", "config": {}},
            {"id": "n2", "type": "filter", "config": {"conditions": []}},
            {"id": "n3", "type": "filter", "config": {"conditions": []}},
        ]
        edges = [
            {"source_node_id": "n1", "target_node_id": "n2"},
            {"source_node_id": "n2", "target_node_id": "n3"},
            {"source_node_id": "n3", "target_node_id": "n2"},
        ]
        errors = validate_workflow(nodes, edges)
        assert any("cycle" in e.lower() for e in errors)

    def test_validate_invalid_edge_reference(self):
        nodes = [{"id": "n1", "type": "manual_trigger", "config": {}}]
        edges = [{"source_node_id": "n1", "target_node_id": "n99"}]
        errors = validate_workflow(nodes, edges)
        assert any("n99" in e for e in errors)

    def test_validate_duplicate_node_ids(self):
        nodes = [
            {"id": "n1", "type": "manual_trigger", "config": {}},
            {"id": "n1", "type": "web_search", "config": {"query_template": "test"}},
        ]
        errors = validate_workflow(nodes, [])
        assert any("Duplicate" in e for e in errors)

    def test_validate_unknown_node_type(self):
        nodes = [{"id": "n1", "type": "nonexistent_type", "config": {}}]
        errors = validate_workflow(nodes, [])
        assert any("Unknown node type" in e for e in errors)


# ── Node Handler Tests ───────────────────────────────────────────────

class TestNodeHandlers:
    def test_manual_trigger(self):
        result = asyncio.get_event_loop().run_until_complete(
            handle_manual_trigger({}, None, {})
        )
        assert result["triggered"] is True
        assert result["trigger_type"] == "manual"

    def test_filter_basic(self):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
            {"name": "Charlie", "age": 35},
        ]
        config = {"conditions": [{"field": "age", "op": "gt", "value": 28}]}
        result = asyncio.get_event_loop().run_until_complete(
            handle_filter(config, data, {})
        )
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Charlie"

    def test_filter_contains(self):
        data = [{"name": "hello world"}, {"name": "goodbye"}]
        config = {"conditions": [{"field": "name", "op": "contains", "value": "hello"}]}
        result = asyncio.get_event_loop().run_until_complete(
            handle_filter(config, data, {})
        )
        assert len(result) == 1

    def test_transform_rename(self):
        data = [{"first_name": "Alice"}]
        config = {"operations": [{"type": "rename", "from": "first_name", "to": "name"}]}
        result = asyncio.get_event_loop().run_until_complete(
            handle_transform(config, data, {})
        )
        assert result[0]["name"] == "Alice"
        assert "first_name" not in result[0]

    def test_merge_concat(self):
        data = {"input_a": [{"id": 1}], "input_b": [{"id": 2}]}
        config = {"strategy": "concat"}
        result = asyncio.get_event_loop().run_until_complete(
            handle_merge(config, data, {})
        )
        assert len(result) == 2

    def test_merge_join(self):
        data = {
            "input_a": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
            "input_b": [{"id": 1, "score": 100}, {"id": 2, "score": 200}],
        }
        config = {"strategy": "join", "key_field": "id"}
        result = asyncio.get_event_loop().run_until_complete(
            handle_merge(config, data, {})
        )
        assert len(result) == 2
        assert result[0]["name"] == "A"
        assert result[0]["score"] == 100

    def test_deduplicate(self):
        data = [{"name": "A"}, {"name": "B"}, {"name": "A"}]
        config = {"match_fields": ["name"]}
        result = asyncio.get_event_loop().run_until_complete(
            handle_deduplicate(config, data, {})
        )
        assert len(result) == 2

    def test_sort_asc(self):
        data = [{"val": 3}, {"val": 1}, {"val": 2}]
        config = {"field": "val", "direction": "asc"}
        result = asyncio.get_event_loop().run_until_complete(
            handle_sort(config, data, {})
        )
        assert [r["val"] for r in result] == [1, 2, 3]

    def test_sort_desc(self):
        data = [{"val": 1}, {"val": 3}, {"val": 2}]
        config = {"field": "val", "direction": "desc"}
        result = asyncio.get_event_loop().run_until_complete(
            handle_sort(config, data, {})
        )
        assert [r["val"] for r in result] == [3, 2, 1]

    def test_aggregate_no_group(self):
        data = [{"val": 10}, {"val": 20}, {"val": 30}]
        config = {"aggregations": [{"field": "val", "func": "sum"}, {"field": "val", "func": "avg"}]}
        result = asyncio.get_event_loop().run_until_complete(
            handle_aggregate(config, data, {})
        )
        assert result["val_sum"] == 60
        assert result["val_avg"] == 20.0

    def test_aggregate_with_group(self):
        data = [
            {"cat": "A", "val": 10},
            {"cat": "A", "val": 20},
            {"cat": "B", "val": 5},
        ]
        config = {"group_by": "cat", "aggregations": [{"field": "val", "func": "sum"}]}
        result = asyncio.get_event_loop().run_until_complete(
            handle_aggregate(config, data, {})
        )
        assert len(result) == 2
        a_group = next(r for r in result if r["cat"] == "A")
        assert a_group["val_sum"] == 30

    def test_condition_true(self):
        config = {"expression": "data.get('score', 0) > 50"}
        result = asyncio.get_event_loop().run_until_complete(
            handle_condition(config, {"score": 80}, {"variables": {}})
        )
        assert result["__condition_result"] is True

    def test_condition_false(self):
        config = {"expression": "data.get('score', 0) > 50"}
        result = asyncio.get_event_loop().run_until_complete(
            handle_condition(config, {"score": 20}, {"variables": {}})
        )
        assert result["__condition_result"] is False

    def test_export_data_json(self):
        data = [{"a": 1}, {"a": 2}]
        config = {"format": "json"}
        result = asyncio.get_event_loop().run_until_complete(
            handle_export_data(config, data, {})
        )
        assert result["format"] == "json"
        assert len(result["data"]) == 2

    def test_export_data_csv(self):
        data = [{"name": "A", "value": 1}, {"name": "B", "value": 2}]
        config = {"format": "csv"}
        result = asyncio.get_event_loop().run_until_complete(
            handle_export_data(config, data, {})
        )
        assert result["format"] == "csv"
        assert "name,value" in result["data"]

    def test_generate_chart(self):
        data = [{"x": "A", "y": 10}, {"x": "B", "y": 20}]
        config = {"chart_type": "bar", "x_field": "x", "y_field": "y"}
        result = asyncio.get_event_loop().run_until_complete(
            handle_generate_chart(config, data, {})
        )
        assert result["chart_type"] == "bar"
        assert len(result["data_points"]) == 2

    def test_execute_handler_unknown_type(self):
        with pytest.raises(ValueError, match="No handler"):
            asyncio.get_event_loop().run_until_complete(
                execute_handler("nonexistent", {}, None, {})
            )

    def test_all_handlers_registered(self):
        from app.services.workflow.node_handlers import HANDLERS
        for node_type in NODE_TYPES:
            assert node_type in HANDLERS, f"Missing handler for {node_type}"


# ── Template Tests ───────────────────────────────────────────────────

class TestTemplates:
    def test_system_templates_defined(self):
        from app.services.workflow.templates import SYSTEM_TEMPLATES
        assert len(SYSTEM_TEMPLATES) == 6

    def test_template_structure(self):
        from app.services.workflow.templates import SYSTEM_TEMPLATES
        for tmpl in SYSTEM_TEMPLATES:
            assert "name" in tmpl
            assert "category" in tmpl
            assert "nodes_template" in tmpl
            assert "edges_template" in tmpl
            assert "variables_schema" in tmpl
            assert len(tmpl["nodes_template"]) > 0

    def test_template_categories(self):
        from app.services.workflow.templates import SYSTEM_TEMPLATES
        categories = {t["category"] for t in SYSTEM_TEMPLATES}
        expected = {"real_estate", "competitive_intel", "local_business", "due_diligence", "price_monitoring", "people_research"}
        assert categories == expected

    def test_template_variables_have_names(self):
        from app.services.workflow.templates import SYSTEM_TEMPLATES
        for tmpl in SYSTEM_TEMPLATES:
            for var in tmpl["variables_schema"]:
                assert "name" in var, f"Variable missing name in {tmpl['name']}"
                assert "type" in var, f"Variable missing type in {tmpl['name']}"


# ── NL Builder Tests ─────────────────────────────────────────────────

class TestNLBuilder:
    def test_fallback_workflow(self):
        from app.services.workflow.nl_builder import NLWorkflowBuilder
        builder = NLWorkflowBuilder()
        result = builder._fallback_workflow("search for restaurants")
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 3
        assert result["nodes"][0]["type"] == "manual_trigger"

    def test_validate_result_valid(self):
        from app.services.workflow.nl_builder import NLWorkflowBuilder
        builder = NLWorkflowBuilder()
        result = {
            "nodes": [
                {"id": "n1", "type": "manual_trigger", "config": {}},
                {"id": "n2", "type": "web_search", "config": {"query_template": "test"}},
            ],
            "edges": [{"source_node_id": "n1", "target_node_id": "n2"}],
        }
        errors = builder._validate_result(result)
        assert errors == []

    def test_validate_result_empty(self):
        from app.services.workflow.nl_builder import NLWorkflowBuilder
        builder = NLWorkflowBuilder()
        errors = builder._validate_result({"nodes": [], "edges": []})
        assert len(errors) > 0

    def test_ensure_ids(self):
        from app.services.workflow.nl_builder import NLWorkflowBuilder
        builder = NLWorkflowBuilder()
        result = {"nodes": [{"id": "", "type": "manual_trigger"}]}
        fixed = builder._ensure_ids(result)
        assert fixed["nodes"][0]["id"] != ""
