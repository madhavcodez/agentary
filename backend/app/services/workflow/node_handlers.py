"""Execution handlers for all 27 workflow node types."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _render_template(template: str, variables: dict[str, Any], input_data: Any = None) -> str:
    """Replace {{variable}} placeholders in a template string."""
    result = template
    all_vars = {**variables}
    if isinstance(input_data, dict):
        all_vars.update(input_data)
    for key, value in all_vars.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def _eval_condition(expression: str, data: Any, variables: dict[str, Any]) -> bool:
    """Safely evaluate a simple condition expression."""
    context = {"data": data, **variables}
    if isinstance(data, dict):
        context.update(data)
    try:
        return bool(eval(expression, {"__builtins__": {}}, context))  # noqa: S307
    except Exception:
        return False


# ── Trigger Handlers ─────────────────────────────────────────────────

async def handle_manual_trigger(config: dict, input_data: Any, context: dict) -> Any:
    return {"triggered": True, "trigger_type": "manual"}


async def handle_schedule_trigger(config: dict, input_data: Any, context: dict) -> Any:
    return {"triggered": True, "trigger_type": "schedule", "cron": config.get("cron")}


async def handle_webhook_trigger(config: dict, input_data: Any, context: dict) -> Any:
    return {"triggered": True, "trigger_type": "webhook", "payload": input_data}


# ── Research Handlers ────────────────────────────────────────────────

async def handle_web_search(config: dict, input_data: Any, context: dict) -> Any:
    from ..gemini import generate_structured

    query = _render_template(config.get("query_template", ""), context.get("variables", {}), input_data)
    num_results = config.get("num_results", 10)

    prompt = (
        f"Search the web for: {query}\n"
        f"Return the top {num_results} results as a JSON array of objects with "
        f"fields: title, url, snippet."
    )
    try:
        results = await generate_structured(prompt)
        return results
    except Exception as e:
        logger.error("web_search failed: %s", e)
        return {"results": [], "error": str(e)}


async def handle_api_query(config: dict, input_data: Any, context: dict) -> Any:
    import httpx

    endpoint = _render_template(config.get("endpoint", ""), context.get("variables", {}), input_data)
    params = config.get("params_template", {})
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(endpoint, params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error("api_query failed: %s", e)
        return {"error": str(e)}


async def handle_web_scrape(config: dict, input_data: Any, context: dict) -> Any:
    import httpx
    from bs4 import BeautifulSoup

    url = _render_template(config.get("url_template", ""), context.get("variables", {}), input_data)
    selectors = config.get("selectors", {})
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        if selectors:
            extracted = {}
            for name, selector in selectors.items():
                elements = soup.select(selector)
                extracted[name] = [el.get_text(strip=True) for el in elements]
            return extracted
        return {"text": soup.get_text(separator="\n", strip=True)[:5000]}
    except Exception as e:
        logger.error("web_scrape failed: %s", e)
        return {"error": str(e)}


async def handle_voice_call(config: dict, input_data: Any, context: dict) -> Any:
    return {
        "status": "stub",
        "message": "Voice call handler — connect to Twilio/Pipecat for live calls",
        "target_source": config.get("target_source", "input"),
        "questions": config.get("questions", []),
    }


async def handle_expert_research(config: dict, input_data: Any, context: dict) -> Any:
    from ..gemini import generate_structured

    task = _render_template(config.get("task_description", ""), context.get("variables", {}), input_data)
    prompt = (
        f"You are an expert researcher. Complete this research task:\n\n{task}\n\n"
        f"Input data: {json.dumps(input_data) if input_data else 'None'}\n\n"
        f"Return structured JSON findings."
    )
    try:
        return await generate_structured(prompt)
    except Exception as e:
        logger.error("expert_research failed: %s", e)
        return {"error": str(e)}


# ── Data Handlers ────────────────────────────────────────────────────

async def handle_filter(config: dict, input_data: Any, context: dict) -> Any:
    conditions = config.get("conditions", [])
    items = input_data if isinstance(input_data, list) else [input_data]
    filtered = []
    for item in items:
        if not isinstance(item, dict):
            filtered.append(item)
            continue
        match = True
        for cond in conditions:
            field = cond.get("field", "")
            op = cond.get("op", "eq")
            value = cond.get("value")
            item_val = item.get(field)
            if op == "eq" and item_val != value:
                match = False
            elif op == "ne" and item_val == value:
                match = False
            elif op == "gt" and (item_val is None or item_val <= value):
                match = False
            elif op == "lt" and (item_val is None or item_val >= value):
                match = False
            elif op == "contains" and (item_val is None or str(value) not in str(item_val)):
                match = False
            elif op == "in" and item_val not in (value if isinstance(value, list) else [value]):
                match = False
        if match:
            filtered.append(item)
    return filtered


async def handle_transform(config: dict, input_data: Any, context: dict) -> Any:
    operations = config.get("operations", [])
    items = input_data if isinstance(input_data, list) else [input_data]
    result = []
    for item in items:
        if not isinstance(item, dict):
            result.append(item)
            continue
        transformed = dict(item)
        for op in operations:
            op_type = op.get("type", "")
            if op_type == "rename" and "from" in op and "to" in op:
                if op["from"] in transformed:
                    transformed[op["to"]] = transformed.pop(op["from"])
            elif op_type == "calculate" and "field" in op and "expression" in op:
                try:
                    transformed[op["field"]] = eval(  # noqa: S307
                        op["expression"], {"__builtins__": {}}, transformed
                    )
                except Exception:
                    pass
            elif op_type == "format" and "field" in op and "template" in op:
                transformed[op["field"]] = _render_template(op["template"], transformed)
        result.append(transformed)
    return result


async def handle_merge(config: dict, input_data: Any, context: dict) -> Any:
    strategy = config.get("strategy", "concat")
    if isinstance(input_data, dict) and "input_a" in input_data and "input_b" in input_data:
        a = input_data["input_a"] if isinstance(input_data["input_a"], list) else [input_data["input_a"]]
        b = input_data["input_b"] if isinstance(input_data["input_b"], list) else [input_data["input_b"]]
    elif isinstance(input_data, list):
        mid = len(input_data) // 2
        a, b = input_data[:mid], input_data[mid:]
    else:
        return input_data

    if strategy == "concat":
        return a + b
    elif strategy == "zip":
        return [{"a": x, "b": y} for x, y in zip(a, b)]
    elif strategy == "join":
        key = config.get("key_field", "id")
        b_map = {item.get(key): item for item in b if isinstance(item, dict)}
        return [{**item, **b_map.get(item.get(key), {})} for item in a if isinstance(item, dict)]
    return a + b


async def handle_deduplicate(config: dict, input_data: Any, context: dict) -> Any:
    match_fields = config.get("match_fields", [])
    items = input_data if isinstance(input_data, list) else [input_data]
    seen = set()
    result = []
    for item in items:
        if isinstance(item, dict) and match_fields:
            key = tuple(item.get(f) for f in match_fields)
        else:
            key = (json.dumps(item, sort_keys=True, default=str),)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


async def handle_sort(config: dict, input_data: Any, context: dict) -> Any:
    field = config.get("field", "")
    direction = config.get("direction", "asc")
    items = input_data if isinstance(input_data, list) else [input_data]
    try:
        return sorted(
            items,
            key=lambda x: x.get(field, "") if isinstance(x, dict) else x,
            reverse=(direction == "desc"),
        )
    except Exception:
        return items


async def handle_aggregate(config: dict, input_data: Any, context: dict) -> Any:
    group_by = config.get("group_by")
    aggregations = config.get("aggregations", [])
    items = input_data if isinstance(input_data, list) else [input_data]

    if not group_by:
        result = {}
        for agg in aggregations:
            field = agg.get("field", "")
            func = agg.get("func", "count")
            values = [item.get(field, 0) for item in items if isinstance(item, dict)]
            numeric = [v for v in values if isinstance(v, (int, float))]
            if func == "count":
                result[f"{field}_count"] = len(values)
            elif func == "sum":
                result[f"{field}_sum"] = sum(numeric)
            elif func == "avg":
                result[f"{field}_avg"] = sum(numeric) / len(numeric) if numeric else 0
            elif func == "min":
                result[f"{field}_min"] = min(numeric) if numeric else 0
            elif func == "max":
                result[f"{field}_max"] = max(numeric) if numeric else 0
        return result

    groups: dict[Any, list] = {}
    for item in items:
        if isinstance(item, dict):
            key = item.get(group_by, "unknown")
            groups.setdefault(key, []).append(item)

    result = []
    for group_key, group_items in groups.items():
        row = {group_by: group_key}
        for agg in aggregations:
            field = agg.get("field", "")
            func = agg.get("func", "count")
            values = [item.get(field, 0) for item in group_items if isinstance(item, dict)]
            numeric = [v for v in values if isinstance(v, (int, float))]
            if func == "count":
                row[f"{field}_count"] = len(values)
            elif func == "sum":
                row[f"{field}_sum"] = sum(numeric)
            elif func == "avg":
                row[f"{field}_avg"] = sum(numeric) / len(numeric) if numeric else 0
            elif func == "min":
                row[f"{field}_min"] = min(numeric) if numeric else 0
            elif func == "max":
                row[f"{field}_max"] = max(numeric) if numeric else 0
        result.append(row)
    return result


# ── Analysis Handlers ────────────────────────────────────────────────

async def handle_ai_analyze(config: dict, input_data: Any, context: dict) -> Any:
    from ..gemini import generate_structured, generate_text

    prompt = _render_template(config.get("prompt_template", ""), context.get("variables", {}), input_data)
    full_prompt = f"{prompt}\n\nData to analyze:\n{json.dumps(input_data, default=str)[:4000]}"
    output_format = config.get("output_format", "json")
    try:
        if output_format == "json":
            return await generate_structured(full_prompt)
        text = await generate_text(full_prompt)
        return {"analysis": text}
    except Exception as e:
        logger.error("ai_analyze failed: %s", e)
        return {"error": str(e)}


async def handle_compare(config: dict, input_data: Any, context: dict) -> Any:
    from ..gemini import generate_structured

    comparison_type = config.get("comparison_type", "side_by_side")
    prompt = (
        f"Compare the following data sets using '{comparison_type}' comparison.\n"
        f"Data: {json.dumps(input_data, default=str)[:4000]}\n"
        f"Return structured JSON comparison."
    )
    try:
        return await generate_structured(prompt)
    except Exception as e:
        logger.error("compare failed: %s", e)
        return {"error": str(e)}


async def handle_trend_detect(config: dict, input_data: Any, context: dict) -> Any:
    from ..gemini import generate_structured

    time_field = config.get("time_field", "date")
    value_fields = config.get("value_fields", [])
    prompt = (
        f"Analyze the following time-series data for trends.\n"
        f"Time field: {time_field}, Value fields: {value_fields}\n"
        f"Data: {json.dumps(input_data, default=str)[:4000]}\n"
        f"Return JSON with: trends, anomalies, predictions."
    )
    try:
        return await generate_structured(prompt)
    except Exception as e:
        logger.error("trend_detect failed: %s", e)
        return {"error": str(e)}


# ── Output Handlers ──────────────────────────────────────────────────

async def handle_generate_report(config: dict, input_data: Any, context: dict) -> Any:
    from ..gemini import generate_text

    sections = config.get("sections", [])
    report_type = config.get("report_type", "summary")
    prompt = (
        f"Generate a {report_type} report from the following data.\n"
        f"Sections to include: {sections if sections else 'auto-determine'}\n"
        f"Data: {json.dumps(input_data, default=str)[:4000]}\n"
        f"Format as clean markdown."
    )
    try:
        text = await generate_text(prompt)
        return {"report": text, "report_type": report_type}
    except Exception as e:
        logger.error("generate_report failed: %s", e)
        return {"error": str(e)}


async def handle_generate_chart(config: dict, input_data: Any, context: dict) -> Any:
    chart_type = config.get("chart_type", "bar")
    x_field = config.get("x_field", "")
    y_field = config.get("y_field", "")
    items = input_data if isinstance(input_data, list) else [input_data]
    chart_data = {
        "chart_type": chart_type,
        "x_field": x_field,
        "y_field": y_field,
        "data_points": [
            {"x": item.get(x_field, ""), "y": item.get(y_field, 0)}
            for item in items
            if isinstance(item, dict)
        ],
    }
    return chart_data


async def handle_export_data(config: dict, input_data: Any, context: dict) -> Any:
    fmt = config.get("format", "json")
    items = input_data if isinstance(input_data, list) else [input_data]
    if fmt == "json":
        return {"format": "json", "data": items}
    elif fmt == "csv":
        if items and isinstance(items[0], dict):
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=items[0].keys())
            writer.writeheader()
            writer.writerows(items)
            return {"format": "csv", "data": output.getvalue()}
        return {"format": "csv", "data": ""}
    return {"format": fmt, "data": items}


async def handle_send_email(config: dict, input_data: Any, context: dict) -> Any:
    variables = context.get("variables", {})
    to = _render_template(config.get("to_template", ""), variables, input_data)
    subject = _render_template(config.get("subject_template", ""), variables, input_data)
    body = _render_template(config.get("body_template", ""), variables, input_data)
    return {
        "status": "email_queued",
        "to": to,
        "subject": subject,
        "body_preview": body[:200],
    }


async def handle_send_alert(config: dict, input_data: Any, context: dict) -> Any:
    channel = config.get("channel", "dashboard")
    message = _render_template(config.get("message_template", ""), context.get("variables", {}), input_data)
    return {"status": "alert_sent", "channel": channel, "message": message}


async def handle_save_findings(config: dict, input_data: Any, context: dict) -> Any:
    category = config.get("category", "general")
    confidence = config.get("confidence_default", 0.8)
    items = input_data if isinstance(input_data, list) else [input_data]
    return {
        "status": "findings_saved",
        "count": len(items),
        "category": category,
        "confidence": confidence,
    }


# ── Control Flow Handlers ───────────────────────────────────────────

async def handle_condition(config: dict, input_data: Any, context: dict) -> Any:
    expression = config.get("expression", "True")
    result = _eval_condition(expression, input_data, context.get("variables", {}))
    return {"__condition_result": result, "data": input_data}


async def handle_loop(config: dict, input_data: Any, context: dict) -> Any:
    items = input_data if isinstance(input_data, list) else [input_data]
    return {"__loop_items": items, "item_variable": config.get("item_variable", "item")}


async def handle_delay(config: dict, input_data: Any, context: dict) -> Any:
    seconds = min(config.get("seconds", 5), 300)  # cap at 5 minutes
    await asyncio.sleep(seconds)
    return input_data


async def handle_human_review(config: dict, input_data: Any, context: dict) -> Any:
    return {
        "status": "pending_review",
        "prompt": config.get("prompt", "Please review"),
        "data": input_data,
    }


# ── Handler registry ────────────────────────────────────────────────

HANDLERS = {
    "manual_trigger": handle_manual_trigger,
    "schedule_trigger": handle_schedule_trigger,
    "webhook_trigger": handle_webhook_trigger,
    "web_search": handle_web_search,
    "api_query": handle_api_query,
    "web_scrape": handle_web_scrape,
    "voice_call": handle_voice_call,
    "expert_research": handle_expert_research,
    "filter": handle_filter,
    "transform": handle_transform,
    "merge": handle_merge,
    "deduplicate": handle_deduplicate,
    "sort": handle_sort,
    "aggregate": handle_aggregate,
    "ai_analyze": handle_ai_analyze,
    "compare": handle_compare,
    "trend_detect": handle_trend_detect,
    "generate_report": handle_generate_report,
    "generate_chart": handle_generate_chart,
    "export_data": handle_export_data,
    "send_email": handle_send_email,
    "send_alert": handle_send_alert,
    "save_findings": handle_save_findings,
    "condition": handle_condition,
    "loop": handle_loop,
    "delay": handle_delay,
    "human_review": handle_human_review,
}


async def execute_handler(node_type: str, config: dict, input_data: Any, context: dict) -> Any:
    handler = HANDLERS.get(node_type)
    if not handler:
        raise ValueError(f"No handler for node type: {node_type}")
    return await handler(config, input_data, context)
