"""Workflow service — CRUD, validation, template instantiation, and run orchestration."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.workflow import Workflow
from ...models.workflow_run import WorkflowRun
from ...models.workflow_template import WorkflowTemplate
from .node_registry import NODE_TYPES, validate_node_config

logger = logging.getLogger(__name__)


# ── Validation ───────────────────────────────────────────────────────

def validate_workflow(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Validate workflow structure. Returns list of errors."""
    errors = []

    if not nodes:
        errors.append("Workflow must have at least one node")
        return errors

    node_ids = {n.get("id") for n in nodes}

    # Check for duplicate node IDs
    if len(node_ids) != len(nodes):
        errors.append("Duplicate node IDs found")

    # Check all edge references are valid
    for edge in edges:
        src = edge.get("source_node_id", edge.get("source", ""))
        tgt = edge.get("target_node_id", edge.get("target", ""))
        if src not in node_ids:
            errors.append(f"Edge references unknown source node: {src}")
        if tgt not in node_ids:
            errors.append(f"Edge references unknown target node: {tgt}")

    # Check for orphan nodes (no edges, except triggers)
    connected = set()
    for edge in edges:
        connected.add(edge.get("source_node_id", edge.get("source", "")))
        connected.add(edge.get("target_node_id", edge.get("target", "")))
    for node in nodes:
        nid = node.get("id")
        ntype = node.get("type", "")
        if nid not in connected and not ntype.endswith("_trigger") and len(nodes) > 1:
            errors.append(f"Orphan node (no connections): {nid}")

    # Check for cycles via topological sort
    in_degree: dict[str, int] = dict.fromkeys(node_ids, 0)
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = edge.get("source_node_id", edge.get("source", ""))
        tgt = edge.get("target_node_id", edge.get("target", ""))
        if src in node_ids and tgt in node_ids:
            adj[src].append(tgt)
            in_degree[tgt] = in_degree.get(tgt, 0) + 1
    queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
    visited = 0
    while queue:
        node_id = queue.popleft()
        visited += 1
        for neighbor in adj[node_id]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    if visited != len(node_ids):
        errors.append("Workflow contains a cycle")

    # Validate node configs
    for node in nodes:
        ntype = node.get("type", "")
        config = node.get("config", {})
        if ntype not in NODE_TYPES:
            errors.append(f"Unknown node type: {ntype}")
        else:
            config_errors = validate_node_config(ntype, config)
            errors.extend(config_errors)

    return errors


# ── CRUD ─────────────────────────────────────────────────────────────

def create_workflow(db: Session, user_id: UUID, data: dict[str, Any]) -> Workflow:
    workflow = Workflow(
        user_id=user_id,
        project_id=data.get("project_id"),
        name=data["name"],
        description=data.get("description"),
        status=data.get("status", "draft"),
        trigger_type=data.get("trigger_type", "manual"),
        trigger_config=data.get("trigger_config"),
        created_from=data.get("created_from", "visual_editor"),
        template_id=data.get("template_id"),
        nodes=data.get("nodes", []),
        edges=data.get("edges", []),
        variables=data.get("variables", {}),
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


def update_workflow(db: Session, workflow: Workflow, data: dict[str, Any]) -> Workflow:
    for field in ["name", "description", "status", "trigger_type", "trigger_config", "nodes", "edges", "variables"]:
        if field in data and data[field] is not None:
            setattr(workflow, field, data[field])
    db.commit()
    db.refresh(workflow)
    return workflow


def delete_workflow(db: Session, workflow: Workflow) -> None:
    db.delete(workflow)
    db.commit()


# ── Template Instantiation ──────────────────────────────────────────

def create_from_template(
    db: Session, user_id: UUID, template_id: UUID, variables: dict[str, Any],
    project_id: UUID | None = None, name: str | None = None,
) -> Workflow:
    template = db.query(WorkflowTemplate).filter(WorkflowTemplate.id == template_id).first()
    if not template:
        raise ValueError(f"Template {template_id} not found")

    # Validate required variables
    for var_def in (template.variables_schema or []):
        if var_def.get("required") and var_def["name"] not in variables:
            if "default" not in var_def:
                raise ValueError(f"Missing required variable: {var_def['name']}")
            variables[var_def["name"]] = var_def["default"]

    workflow = Workflow(
        user_id=user_id,
        project_id=project_id,
        name=name or f"{template.name} — Copy",
        description=template.description,
        status="draft",
        trigger_type="manual",
        created_from="template",
        template_id=template_id,
        nodes=template.nodes_template or [],
        edges=template.edges_template or [],
        variables=variables,
    )
    db.add(workflow)

    # Increment install count
    template.install_count = (template.install_count or 0) + 1
    db.commit()
    db.refresh(workflow)
    return workflow


# ── NL Creation ──────────────────────────────────────────────────────

async def create_from_natural_language(
    db: Session, user_id: UUID, description: str, project_id: UUID | None = None,
) -> Workflow:
    from .nl_builder import NLWorkflowBuilder

    builder = NLWorkflowBuilder()
    result = await builder.build_workflow(description)

    workflow = Workflow(
        user_id=user_id,
        project_id=project_id,
        name=result.get("name", "Generated Workflow"),
        description=description,
        status="draft",
        trigger_type=result.get("trigger_type", "manual"),
        trigger_config=result.get("trigger_config"),
        created_from="natural_language",
        nodes=result.get("nodes", []),
        edges=result.get("edges", []),
        variables=result.get("variables", {}),
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


# ── Run Orchestration ────────────────────────────────────────────────

async def trigger_run(db: Session, workflow: Workflow, trigger: str = "manual") -> WorkflowRun:
    from .executor import WorkflowExecutor

    run = WorkflowRun(
        workflow_id=workflow.id,
        user_id=workflow.user_id,
        status="queued",
        trigger_type=trigger,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    executor = WorkflowExecutor(db)
    run = await executor.execute_run(run.id)
    return run


def activate_workflow(db: Session, workflow: Workflow) -> Workflow:
    errors = validate_workflow(workflow.nodes or [], workflow.edges or [])
    if errors:
        raise ValueError(f"Workflow validation failed: {'; '.join(errors)}")

    workflow.status = "active"
    db.commit()
    db.refresh(workflow)

    # Register schedule if applicable
    if workflow.trigger_type == "scheduled" and workflow.trigger_config:
        from ..scheduler import add_workflow_schedule
        cron = workflow.trigger_config.get("cron", "0 9 * * *")
        tz = workflow.trigger_config.get("timezone", "America/Los_Angeles")
        add_workflow_schedule(str(workflow.id), cron, tz)

    return workflow


def pause_workflow(db: Session, workflow: Workflow) -> Workflow:
    workflow.status = "paused"
    db.commit()
    db.refresh(workflow)

    if workflow.trigger_type == "scheduled":
        from ..scheduler import remove_workflow_schedule
        remove_workflow_schedule(str(workflow.id))

    return workflow
