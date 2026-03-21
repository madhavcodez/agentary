"""Chart.js configuration generator for data visualization."""
from __future__ import annotations

from typing import Any

TOOL_SCHEMA: dict[str, Any] = {
    "name": "chart_generator",
    "description": "Generate a Chart.js configuration object for data visualization. Returns JSON config ready for rendering.",
    "parameters": {
        "type": "object",
        "properties": {
            "chart_type": {
                "type": "string",
                "description": "Type of chart to generate",
                "enum": ["line", "bar", "pie", "doughnut", "scatter", "radar"],
            },
            "title": {
                "type": "string",
                "description": "Chart title",
            },
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "X-axis labels or category names",
            },
            "datasets": {
                "type": "array",
                "description": "Data series. Each item: {label, data: number[], color?}",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "data": {"type": "array", "items": {"type": "number"}},
                        "color": {"type": "string"},
                    },
                    "required": ["label", "data"],
                },
            },
            "x_label": {"type": "string", "description": "X-axis label"},
            "y_label": {"type": "string", "description": "Y-axis label"},
        },
        "required": ["chart_type", "title", "labels", "datasets"],
    },
}

DEFAULT_COLORS = [
    "rgba(59, 130, 246, 0.8)",   # blue
    "rgba(16, 185, 129, 0.8)",   # green
    "rgba(245, 158, 11, 0.8)",   # amber
    "rgba(239, 68, 68, 0.8)",    # red
    "rgba(139, 92, 246, 0.8)",   # purple
    "rgba(236, 72, 153, 0.8)",   # pink
    "rgba(14, 165, 233, 0.8)",   # sky
    "rgba(249, 115, 22, 0.8)",   # orange
]


async def execute(
    chart_type: str,
    title: str,
    labels: list[str],
    datasets: list[dict[str, Any]],
    x_label: str = "",
    y_label: str = "",
    **kwargs: Any,
) -> dict[str, Any]:
    """Generate a Chart.js config."""
    chartjs_datasets = []
    for i, ds in enumerate(datasets):
        color = ds.get("color", DEFAULT_COLORS[i % len(DEFAULT_COLORS)])
        border_color = color.replace("0.8)", "1)")
        chartjs_datasets.append({
            "label": ds["label"],
            "data": ds["data"],
            "backgroundColor": color,
            "borderColor": border_color,
            "borderWidth": 2,
            "fill": chart_type == "line",
            "tension": 0.3 if chart_type == "line" else 0,
        })

    config: dict[str, Any] = {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": chartjs_datasets,
        },
        "options": {
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": title},
                "legend": {"display": len(datasets) > 1},
            },
        },
    }

    if chart_type in ("line", "bar", "scatter"):
        config["options"]["scales"] = {
            "x": {"title": {"display": bool(x_label), "text": x_label}},
            "y": {"title": {"display": bool(y_label), "text": y_label}},
        }

    return {
        "tool": "chart_generator",
        "chart_config": config,
        "chart_type": chart_type,
        "title": title,
        "status": "success",
    }
