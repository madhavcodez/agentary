"""Registry of all workflow node types with config schemas and metadata."""

from __future__ import annotations

from typing import Any

# ── Node type definitions ────────────────────────────────────────────

NODE_TYPES: dict[str, dict[str, Any]] = {
    # ── Trigger Nodes ────────────────────────────────────────────────
    "manual_trigger": {
        "category": "trigger",
        "label": "Manual Trigger",
        "description": "Start workflow manually",
        "config_schema": {},
        "inputs": [],
        "outputs": ["output"],
    },
    "schedule_trigger": {
        "category": "trigger",
        "label": "Schedule Trigger",
        "description": "Run on a cron schedule",
        "config_schema": {
            "cron": {"type": "string", "required": True, "description": "Cron expression (e.g. '0 9 * * 1-5')"},
            "timezone": {"type": "string", "required": False, "default": "America/Los_Angeles"},
        },
        "inputs": [],
        "outputs": ["output"],
    },
    "webhook_trigger": {
        "category": "trigger",
        "label": "Webhook Trigger",
        "description": "Trigger from external webhook",
        "config_schema": {
            "secret": {"type": "string", "required": False, "description": "Webhook secret for validation"},
        },
        "inputs": [],
        "outputs": ["output"],
    },

    # ── Research Nodes ───────────────────────────────────────────────
    "web_search": {
        "category": "research",
        "label": "Web Search",
        "description": "Search the web for information",
        "config_schema": {
            "query_template": {"type": "string", "required": True, "description": "Search query (supports {{variables}})"},
            "num_results": {"type": "integer", "required": False, "default": 10},
            "search_engine": {"type": "string", "required": False, "default": "gemini", "options": ["gemini", "exa"]},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "api_query": {
        "category": "research",
        "label": "API Query",
        "description": "Query an external API",
        "config_schema": {
            "source_type": {"type": "string", "required": True, "description": "API source identifier"},
            "endpoint": {"type": "string", "required": True},
            "params_template": {"type": "object", "required": False, "default": {}},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "web_scrape": {
        "category": "research",
        "label": "Web Scrape",
        "description": "Scrape data from web pages",
        "config_schema": {
            "url_template": {"type": "string", "required": True, "description": "URL to scrape (supports {{variables}})"},
            "selectors": {"type": "object", "required": False, "default": {}},
            "extract_fields": {"type": "array", "required": False, "default": []},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "voice_call": {
        "category": "research",
        "label": "Voice Call",
        "description": "Make outbound voice calls to gather information",
        "config_schema": {
            "target_source": {"type": "string", "required": False, "default": "input", "options": ["input", "google_places"]},
            "extraction_template_id": {"type": "string", "required": False},
            "questions": {"type": "array", "required": False, "default": []},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "expert_research": {
        "category": "research",
        "label": "Expert Research",
        "description": "Use a specialized research expert",
        "config_schema": {
            "expert_slug": {"type": "string", "required": True},
            "task_description": {"type": "string", "required": True},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },

    # ── Data Nodes ───────────────────────────────────────────────────
    "filter": {
        "category": "data",
        "label": "Filter",
        "description": "Filter data by conditions",
        "config_schema": {
            "conditions": {
                "type": "array",
                "required": True,
                "items": {
                    "field": {"type": "string"},
                    "op": {"type": "string", "options": ["eq", "ne", "gt", "lt", "contains", "in"]},
                    "value": {"type": "any"},
                },
            },
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "transform": {
        "category": "data",
        "label": "Transform",
        "description": "Transform data fields",
        "config_schema": {
            "operations": {
                "type": "array",
                "required": True,
                "items": {"type": {"type": "string", "options": ["rename", "calculate", "format"]}},
            },
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "merge": {
        "category": "data",
        "label": "Merge",
        "description": "Merge multiple data sources",
        "config_schema": {
            "strategy": {"type": "string", "required": False, "default": "concat", "options": ["concat", "join", "zip"]},
            "key_field": {"type": "string", "required": False},
        },
        "inputs": ["input_a", "input_b"],
        "outputs": ["output"],
    },
    "deduplicate": {
        "category": "data",
        "label": "Deduplicate",
        "description": "Remove duplicate records",
        "config_schema": {
            "match_fields": {"type": "array", "required": True},
            "strategy": {"type": "string", "required": False, "default": "exact", "options": ["exact", "fuzzy"]},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "sort": {
        "category": "data",
        "label": "Sort",
        "description": "Sort data by field",
        "config_schema": {
            "field": {"type": "string", "required": True},
            "direction": {"type": "string", "required": False, "default": "asc", "options": ["asc", "desc"]},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "aggregate": {
        "category": "data",
        "label": "Aggregate",
        "description": "Aggregate data with grouping",
        "config_schema": {
            "group_by": {"type": "string", "required": False},
            "aggregations": {
                "type": "array",
                "required": True,
                "items": {
                    "field": {"type": "string"},
                    "func": {"type": "string", "options": ["count", "sum", "avg", "min", "max"]},
                },
            },
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },

    # ── Analysis Nodes ───────────────────────────────────────────────
    "ai_analyze": {
        "category": "analysis",
        "label": "AI Analysis",
        "description": "Analyze data with AI",
        "config_schema": {
            "prompt_template": {"type": "string", "required": True, "description": "Analysis prompt (supports {{variables}})"},
            "output_format": {"type": "string", "required": False, "default": "json", "options": ["json", "text"]},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "compare": {
        "category": "analysis",
        "label": "Compare",
        "description": "Compare data sets",
        "config_schema": {
            "comparison_type": {"type": "string", "required": False, "default": "side_by_side", "options": ["side_by_side", "diff", "ranking"]},
            "metrics": {"type": "array", "required": False, "default": []},
        },
        "inputs": ["input_a", "input_b"],
        "outputs": ["output"],
    },
    "trend_detect": {
        "category": "analysis",
        "label": "Trend Detection",
        "description": "Detect trends in time-series data",
        "config_schema": {
            "time_field": {"type": "string", "required": True},
            "value_fields": {"type": "array", "required": True},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },

    # ── Output Nodes ─────────────────────────────────────────────────
    "generate_report": {
        "category": "output",
        "label": "Generate Report",
        "description": "Generate a structured report",
        "config_schema": {
            "report_type": {"type": "string", "required": False, "default": "summary"},
            "sections": {"type": "array", "required": False, "default": []},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "generate_chart": {
        "category": "output",
        "label": "Generate Chart",
        "description": "Create a data visualization",
        "config_schema": {
            "chart_type": {"type": "string", "required": True, "options": ["bar", "line", "pie", "scatter"]},
            "x_field": {"type": "string", "required": True},
            "y_field": {"type": "string", "required": True},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "export_data": {
        "category": "output",
        "label": "Export Data",
        "description": "Export data in various formats",
        "config_schema": {
            "format": {"type": "string", "required": False, "default": "json", "options": ["csv", "json", "excel"]},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "send_email": {
        "category": "output",
        "label": "Send Email",
        "description": "Send email notification",
        "config_schema": {
            "to_template": {"type": "string", "required": True},
            "subject_template": {"type": "string", "required": True},
            "body_template": {"type": "string", "required": True},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "send_alert": {
        "category": "output",
        "label": "Send Alert",
        "description": "Send an alert notification",
        "config_schema": {
            "channel": {"type": "string", "required": False, "default": "dashboard", "options": ["email", "dashboard"]},
            "condition": {"type": "string", "required": False},
            "message_template": {"type": "string", "required": True},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "save_findings": {
        "category": "output",
        "label": "Save Findings",
        "description": "Save results as findings",
        "config_schema": {
            "category": {"type": "string", "required": False, "default": "general"},
            "confidence_default": {"type": "number", "required": False, "default": 0.8},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },

    # ── Control Flow Nodes ───────────────────────────────────────────
    "condition": {
        "category": "control",
        "label": "Condition",
        "description": "Branch based on a condition",
        "config_schema": {
            "expression": {"type": "string", "required": True, "description": "JavaScript-like expression"},
            "true_path": {"type": "string", "required": False},
            "false_path": {"type": "string", "required": False},
        },
        "inputs": ["input"],
        "outputs": ["true", "false"],
    },
    "loop": {
        "category": "control",
        "label": "Loop",
        "description": "Iterate over a collection",
        "config_schema": {
            "collection_source": {"type": "string", "required": False, "default": "input"},
            "item_variable": {"type": "string", "required": False, "default": "item"},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "delay": {
        "category": "control",
        "label": "Delay",
        "description": "Wait before continuing",
        "config_schema": {
            "seconds": {"type": "integer", "required": True, "default": 5},
        },
        "inputs": ["input"],
        "outputs": ["output"],
    },
    "human_review": {
        "category": "control",
        "label": "Human Review",
        "description": "Pause for human approval",
        "config_schema": {
            "prompt": {"type": "string", "required": True, "description": "Question for the reviewer"},
            "timeout_hours": {"type": "integer", "required": False, "default": 24},
        },
        "inputs": ["input"],
        "outputs": ["approved", "rejected"],
    },
}


# ── Helper functions ─────────────────────────────────────────────────

CATEGORIES = ["trigger", "research", "data", "analysis", "output", "control"]


def get_node_type(type_name: str) -> dict[str, Any] | None:
    return NODE_TYPES.get(type_name)


def get_node_types_by_category(category: str) -> dict[str, dict[str, Any]]:
    return {k: v for k, v in NODE_TYPES.items() if v["category"] == category}


def get_all_node_types_summary() -> list[dict[str, Any]]:
    """Return a compact summary for NL builder prompts."""
    result = []
    for type_name, info in NODE_TYPES.items():
        result.append({
            "type": type_name,
            "category": info["category"],
            "label": info["label"],
            "description": info["description"],
            "config_fields": list(info["config_schema"].keys()),
            "inputs": info["inputs"],
            "outputs": info["outputs"],
        })
    return result


def validate_node_config(node_type: str, config: dict[str, Any]) -> list[str]:
    """Validate a node's config against its schema. Returns list of errors."""
    info = NODE_TYPES.get(node_type)
    if not info:
        return [f"Unknown node type: {node_type}"]

    errors = []
    schema = info["config_schema"]
    for field_name, field_def in schema.items():
        if isinstance(field_def, dict) and field_def.get("required") and field_name not in config:
            errors.append(f"Node type '{node_type}': missing required field '{field_name}'")
    return errors
