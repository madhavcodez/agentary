"""Natural Language to Workflow converter — uses Gemini to parse descriptions into DAGs."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from .node_registry import get_all_node_types_summary
from .service import validate_workflow

logger = logging.getLogger(__name__)

NL_SYSTEM_PROMPT = """\
You are a workflow builder AI. Convert natural language descriptions into structured workflow DAGs.

Available node types:
{node_types}

Rules:
- Each node needs: id (unique string like "node_1"), type (from the list above), label (human-readable), config (type-specific), position (x/y for visual layout)
- Edges connect nodes: source_node_id, target_node_id, source_port (default "output"), target_port (default "input")
- For condition nodes, use source_port "true" or "false" for branches
- Start workflows with a trigger node (manual_trigger, schedule_trigger, or webhook_trigger)
- Position nodes in a top-to-bottom flow: trigger at y=0, next row at y=150, etc. Space horizontally with x increments of 250
- If the user mentions a schedule, use schedule_trigger with appropriate cron expression
- Extract variables the user might want to customize

Return ONLY valid JSON with this structure:
{{
  "name": "Workflow Name",
  "trigger_type": "manual" | "scheduled" | "event",
  "trigger_config": null | {{"cron": "...", "timezone": "..."}},
  "nodes": [...],
  "edges": [...],
  "variables": {{}}
}}

Example:
User: "Search for restaurants in Austin, scrape their websites, and email me a report"
Response:
{{
  "name": "Austin Restaurant Research",
  "trigger_type": "manual",
  "trigger_config": null,
  "nodes": [
    {{"id": "node_1", "type": "manual_trigger", "label": "Start", "config": {{}}, "position": {{"x": 250, "y": 0}}}},
    {{"id": "node_2", "type": "web_search", "label": "Search Restaurants", "config": {{"query_template": "restaurants in {{{{location}}}}", "num_results": 20}}, "position": {{"x": 250, "y": 150}}}},
    {{"id": "node_3", "type": "web_scrape", "label": "Scrape Websites", "config": {{"url_template": "{{{{url}}}}", "extract_fields": ["menu", "hours", "reviews"]}}, "position": {{"x": 250, "y": 300}}}},
    {{"id": "node_4", "type": "generate_report", "label": "Create Report", "config": {{"report_type": "summary"}}, "position": {{"x": 250, "y": 450}}}},
    {{"id": "node_5", "type": "send_email", "label": "Email Report", "config": {{"to_template": "{{{{email}}}}", "subject_template": "Restaurant Research Report", "body_template": "{{{{report}}}}"}}, "position": {{"x": 250, "y": 600}}}}
  ],
  "edges": [
    {{"source_node_id": "node_1", "target_node_id": "node_2"}},
    {{"source_node_id": "node_2", "target_node_id": "node_3"}},
    {{"source_node_id": "node_3", "target_node_id": "node_4"}},
    {{"source_node_id": "node_4", "target_node_id": "node_5"}}
  ],
  "variables": {{"location": "Austin, TX", "email": ""}}
}}
"""


class NLWorkflowBuilder:
    """Convert natural language descriptions to workflow DAGs using Gemini."""

    async def build_workflow(
        self, description: str, project_context: dict | None = None
    ) -> dict[str, Any]:
        from ..gemini import generate_structured

        node_types_summary = json.dumps(get_all_node_types_summary(), indent=2)
        system = NL_SYSTEM_PROMPT.format(node_types=node_types_summary)

        prompt = f"User description: {description}"
        if project_context:
            prompt += f"\n\nProject context: {json.dumps(project_context)}"

        # Attempt 1
        try:
            result = await generate_structured(prompt, schema_hint=system)
            errors = self._validate_result(result)
            if not errors:
                return self._ensure_ids(result)
        except Exception as e:
            logger.warning("NL builder attempt 1 failed: %s", e)
            result = None
            errors = [str(e)]

        # Attempt 2 with error feedback
        if errors:
            retry_prompt = (
                f"{prompt}\n\n"
                f"Previous attempt had errors: {'; '.join(errors)}\n"
                f"Please fix these issues and return valid JSON."
            )
            try:
                result = await generate_structured(retry_prompt, schema_hint=system)
                retry_errors = self._validate_result(result)
                if not retry_errors:
                    return self._ensure_ids(result)
                logger.warning("NL builder attempt 2 had errors: %s", retry_errors)
            except Exception as e:
                logger.error("NL builder attempt 2 failed: %s", e)

        # Return best-effort result or a fallback
        if result and isinstance(result, dict) and "nodes" in result:
            return self._ensure_ids(result)

        return self._fallback_workflow(description)

    def _validate_result(self, result: dict[str, Any]) -> list[str]:
        if not isinstance(result, dict):
            return ["Result is not a dict"]

        errors = []
        nodes = result.get("nodes", [])
        edges = result.get("edges", [])

        if not nodes:
            errors.append("No nodes generated")
            return errors

        errors.extend(validate_workflow(nodes, edges))
        return errors

    def _ensure_ids(self, result: dict[str, Any]) -> dict[str, Any]:
        """Ensure all nodes have valid IDs."""
        nodes = result.get("nodes", [])
        for node in nodes:
            if not node.get("id"):
                node["id"] = f"node_{uuid.uuid4().hex[:8]}"
        return result

    def _fallback_workflow(self, description: str) -> dict[str, Any]:
        """Return a minimal workflow when Gemini fails."""
        return {
            "name": description[:50],
            "trigger_type": "manual",
            "trigger_config": None,
            "nodes": [
                {
                    "id": "node_1",
                    "type": "manual_trigger",
                    "label": "Start",
                    "config": {},
                    "position": {"x": 250, "y": 0},
                },
                {
                    "id": "node_2",
                    "type": "ai_analyze",
                    "label": "AI Analysis",
                    "config": {"prompt_template": description, "output_format": "json"},
                    "position": {"x": 250, "y": 150},
                },
                {
                    "id": "node_3",
                    "type": "generate_report",
                    "label": "Report",
                    "config": {"report_type": "summary"},
                    "position": {"x": 250, "y": 300},
                },
            ],
            "edges": [
                {"source_node_id": "node_1", "target_node_id": "node_2"},
                {"source_node_id": "node_2", "target_node_id": "node_3"},
            ],
            "variables": {},
        }
