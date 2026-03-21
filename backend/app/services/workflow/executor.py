"""Workflow execution engine — traverses DAG and executes nodes in topological order."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ...models.workflow import Workflow
from ...models.workflow_run import WorkflowRun
from .node_handlers import execute_handler

logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """Execute a workflow run by traversing the DAG in topological order."""

    def __init__(self, db: Session):
        self.db = db

    async def execute_run(self, run_id: UUID) -> WorkflowRun:
        run = self.db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        if not run:
            raise ValueError(f"WorkflowRun {run_id} not found")

        workflow = self.db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
        if not workflow:
            raise ValueError(f"Workflow {run.workflow_id} not found")

        run.status = "running"
        run.started_at = datetime.utcnow()
        run.node_results = {}
        self.db.commit()

        start_time = time.time()
        nodes = workflow.nodes or []
        edges = workflow.edges or []
        variables = workflow.variables or {}

        try:
            execution_order = self._topological_sort(nodes, edges)
            node_outputs: dict[str, Any] = {}
            context = {"variables": variables, "workflow_id": str(workflow.id), "run_id": str(run.id)}

            for node_id in execution_order:
                node = self._find_node(nodes, node_id)
                if not node:
                    continue

                node_type = node.get("type", "")
                config = node.get("config", {})

                # Gather input from upstream edges
                input_data = self._gather_inputs(node_id, edges, node_outputs)

                # Update status
                node_results = dict(run.node_results)
                node_results[node_id] = {"status": "running", "started_at": datetime.utcnow().isoformat()}
                run.node_results = node_results
                self.db.commit()

                node_start = time.time()
                try:
                    output = await execute_handler(node_type, config, input_data, context)

                    # Handle condition branching
                    if node_type == "condition" and isinstance(output, dict) and "__condition_result" in output:
                        condition_result = output["__condition_result"]
                        actual_data = output.get("data")
                        # Store output and determine which downstream path to take
                        node_outputs[node_id] = actual_data
                        node_outputs[f"{node_id}:true"] = actual_data if condition_result else None
                        node_outputs[f"{node_id}:false"] = actual_data if not condition_result else None
                    # Handle loop
                    elif node_type == "loop" and isinstance(output, dict) and "__loop_items" in output:
                        loop_items = output["__loop_items"]
                        item_var = output.get("item_variable", "item")
                        loop_results = []
                        for item in loop_items:
                            loop_context = {**context, "variables": {**variables, item_var: item}}
                            downstream_nodes = self._get_downstream(node_id, edges)
                            for dn_id in downstream_nodes:
                                dn = self._find_node(nodes, dn_id)
                                if dn:
                                    result = await execute_handler(
                                        dn.get("type", ""), dn.get("config", {}), item, loop_context
                                    )
                                    loop_results.append(result)
                        node_outputs[node_id] = loop_results
                        output = loop_results
                    else:
                        node_outputs[node_id] = output

                    node_duration = time.time() - node_start
                    node_results = dict(run.node_results)
                    node_results[node_id] = {
                        "status": "completed",
                        "output": self._truncate_output(output),
                        "duration": round(node_duration, 2),
                        "started_at": node_results[node_id]["started_at"],
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                    run.node_results = node_results
                    self.db.commit()

                except Exception as e:
                    node_duration = time.time() - node_start
                    node_results = dict(run.node_results)
                    node_results[node_id] = {
                        "status": "failed",
                        "error": str(e),
                        "duration": round(node_duration, 2),
                        "started_at": node_results[node_id]["started_at"],
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                    run.node_results = node_results
                    self.db.commit()
                    logger.error("Node %s failed: %s", node_id, e)
                    # Continue execution despite node failure

            # Collect final outputs from terminal nodes
            terminal_nodes = self._get_terminal_nodes(nodes, edges)
            final_output = {}
            for tn_id in terminal_nodes:
                if tn_id in node_outputs:
                    final_output[tn_id] = node_outputs[tn_id]

            total_duration = time.time() - start_time
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.duration_seconds = round(total_duration, 2)
            run.output_data = final_output

            # Update workflow stats
            workflow.last_run_at = datetime.utcnow()
            workflow.total_runs = (workflow.total_runs or 0) + 1
            if workflow.avg_duration_seconds:
                workflow.avg_duration_seconds = (
                    workflow.avg_duration_seconds * (workflow.total_runs - 1) + total_duration
                ) / workflow.total_runs
            else:
                workflow.avg_duration_seconds = total_duration

            self.db.commit()
            return run

        except Exception as e:
            logger.error("Workflow run %s failed: %s", run_id, e)
            run.status = "failed"
            run.completed_at = datetime.utcnow()
            run.duration_seconds = round(time.time() - start_time, 2)
            run.error = {"message": str(e), "type": type(e).__name__}
            self.db.commit()
            return run

    def _topological_sort(self, nodes: list[dict], edges: list[dict]) -> list[str]:
        """Topological sort of the DAG. Raises ValueError if cycle detected."""
        node_ids = {n["id"] for n in nodes}
        in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
        adj: dict[str, list[str]] = defaultdict(list)

        for edge in edges:
            src = edge.get("source_node_id", edge.get("source", ""))
            tgt = edge.get("target_node_id", edge.get("target", ""))
            if src in node_ids and tgt in node_ids:
                adj[src].append(tgt)
                in_degree[tgt] = in_degree.get(tgt, 0) + 1

        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        order = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            for neighbor in adj[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(node_ids):
            raise ValueError("Workflow contains a cycle — cannot execute")

        return order

    def _find_node(self, nodes: list[dict], node_id: str) -> dict | None:
        for n in nodes:
            if n.get("id") == node_id:
                return n
        return None

    def _gather_inputs(self, node_id: str, edges: list[dict], outputs: dict[str, Any]) -> Any:
        """Collect outputs from upstream nodes connected via edges."""
        inputs = {}
        for edge in edges:
            src = edge.get("source_node_id", edge.get("source", ""))
            tgt = edge.get("target_node_id", edge.get("target", ""))
            src_port = edge.get("source_port", "output")
            tgt_port = edge.get("target_port", "input")
            if tgt == node_id:
                # Check for conditional port outputs
                port_key = f"{src}:{src_port}" if src_port in ("true", "false") else src
                value = outputs.get(port_key, outputs.get(src))
                if value is not None:
                    inputs[tgt_port] = value

        if len(inputs) == 0:
            return None
        if len(inputs) == 1:
            return next(iter(inputs.values()))
        return inputs

    def _get_downstream(self, node_id: str, edges: list[dict]) -> list[str]:
        return [
            edge.get("target_node_id", edge.get("target", ""))
            for edge in edges
            if edge.get("source_node_id", edge.get("source", "")) == node_id
        ]

    def _get_terminal_nodes(self, nodes: list[dict], edges: list[dict]) -> list[str]:
        """Find nodes with no outgoing edges."""
        sources = {edge.get("source_node_id", edge.get("source", "")) for edge in edges}
        return [n["id"] for n in nodes if n["id"] not in sources]

    def _truncate_output(self, output: Any, max_size: int = 10000) -> Any:
        """Truncate large outputs to avoid bloating node_results JSONB."""
        import json as json_mod
        try:
            serialized = json_mod.dumps(output, default=str)
            if len(serialized) > max_size:
                return {"__truncated": True, "preview": serialized[:max_size], "original_size": len(serialized)}
            return output
        except Exception:
            return str(output)[:max_size]
