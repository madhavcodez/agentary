"""CrewRunner — THE EXECUTION ENGINE for expert agent crews.

Execution follows the DeerFlow 5-phase research methodology:
  Phase 1 (scout):     Broad exploration to map the research landscape
  Phase 2 (research):  Parallel deep dives per dimension
  Phase 3 (gap_check): Audit completeness, spawn follow-up research if needed
  Phase 4 (synthesis): Combine findings, resolve contradictions
  Phase 5 (report):    Generate structured output
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from google.genai import types
from sqlalchemy.orm import Session

from ...core.correlation import get_correlation_id
from ...core.events import Event, EventType, event_bus
from ...models.agent_crew import AgentCrew
from ...models.crew_run import CrewRun
from ...models.crew_task import CrewTask
from ...models.enums import FailureCategory, RunStatus
from ...models.expert_agent import ExpertAgent
from ...models.finding import Finding, FindingType, SourceType
from ...models.mission import Mission, MissionStatus
from ...models.run_step import RunStep, StepType
from ...models.signal import SignalSourceType, SignalType
from ..gemini import get_client
from ..intelligence.signal_service import SignalService
from ..state_machine import InvalidTransition
from ..state_machine import transition as sm_transition
from .events import (
    emit_crew_run_completed,
    emit_crew_run_started,
    emit_expert_thinking,
    emit_finding_added,
    emit_task_completed,
    emit_task_started,
)
from .tool_registry import tool_registry

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────
_DEFAULT_MODEL = "gemini-2.5-flash"
_MAX_TOOL_ITERATIONS = 6
_TOKEN_COST_PER_TOKEN = 1e-6
_API_TIMEOUT_MS = 120_000
_TASK_TIMEOUT_SECONDS = 300


def _truncate(data: Any, max_chars: int = 2000) -> Any:
    """Truncate data to fit within *max_chars* when serialised as JSON."""
    if data is None:
        return None
    if isinstance(data, dict):
        serialised = json.dumps(data, default=str)
        if len(serialised) > max_chars:
            return {"_truncated": True, "preview": serialised[:max_chars]}
        return data
    return data


class CrewRunner:
    """Executes a crew run with parallel expert research and agentic tool-calling loops."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Observability: RunStep recording ──────────────────────────────

    def _record_step(
        self,
        run_id: uuid.UUID,
        run_type: str,
        step_type: StepType,
        step_name: str,
        status: str,
        *,
        input_summary: Any = None,
        output_summary: Any = None,
        error: dict | None = None,
        tokens_used: int | None = None,
        duration_ms: int | None = None,
        correlation_id: str | None = None,
        parent_step_id: uuid.UUID | None = None,
    ) -> RunStep:
        """Create and persist a RunStep trace record."""
        cid = correlation_id or get_correlation_id() or None
        step = RunStep(
            run_id=run_id,
            run_type=run_type,
            correlation_id=uuid.UUID(cid) if cid else None,
            step_type=step_type,
            step_name=step_name,
            status=status,
            input_summary=_truncate(input_summary, 2000),
            output_summary=_truncate(output_summary, 5000),
            error=error,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
            parent_step_id=parent_step_id,
            completed_at=(datetime.now(UTC) if status in ("completed", "failed") else None),
        )
        self.db.add(step)
        self.db.flush()
        return step

    async def _transition_run(
        self,
        run: CrewRun,
        target: RunStatus,
        reason: str | None = None,
        mission: Mission | None = None,
    ) -> None:
        """Validate and apply a state transition on a run, persisting the record."""
        current_str = run.status if isinstance(run.status, str) else run.status.value
        current = RunStatus(current_str) if isinstance(current_str, str) else current_str
        record = sm_transition(current, target, reason)
        run.status = target.value
        transitions = list(run.state_transitions or [])
        transitions.append(record)
        run.state_transitions = transitions
        self.db.commit()

        # Emit lifecycle event
        await event_bus.broadcast(
            Event(
                event_type=EventType.run_state_changed,
                data={
                    "run_type": "crew",
                    "run_id": str(run.id),
                    "from_state": record["from"],
                    "to_state": record["to"],
                    "reason": reason,
                },
                project_id=str(mission.project_id) if mission else None,
                mission_id=str(mission.id) if mission else None,
            )
        )

    async def execute_run(self, run_id: uuid.UUID) -> CrewRun:
        """Main execution entry point — DeerFlow 5-phase methodology.

        1. Load run, crew, mission, experts
        2. Emit CREW_RUN_STARTED
        3. SCOUT PHASE: Broad exploration to map research dimensions
        4. RESEARCH PHASE: Parallel deep dives per dimension
        5. GAP CHECK PHASE: Audit completeness, spawn follow-up research
        6. SYNTHESIS PHASE: Synthesizer receives all findings
        7. REPORT PHASE: ReportWriter generates structured output
        8. Emit CREW_RUN_COMPLETED
        """
        run = self.db.query(CrewRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError(f"CrewRun {run_id} not found")

        mission = self.db.query(Mission).filter_by(id=run.mission_id).first()
        crew = self.db.query(AgentCrew).filter_by(mission_id=run.mission_id).first()

        if not crew or not mission:
            run.failure_category = FailureCategory.validation
            run.failure_message = "Crew or mission not found"
            try:
                await self._transition_run(
                    run, RunStatus.failed, "Crew or mission not found", mission
                )
            except InvalidTransition:
                current_status = run.status if isinstance(run.status, str) else run.status.value
                run.status = "failed"
                transitions = list(run.state_transitions or [])
                transitions.append(
                    {
                        "from": current_status,
                        "to": "failed",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "reason": "InvalidTransition fallback — forced to failed",
                    }
                )
                run.state_transitions = transitions
                self.db.commit()
            run.error = {"message": "Crew or mission not found"}
            self.db.commit()
            raise ValueError("Crew or mission not found")

        # Load experts from crew.agents JSONB
        agent_ids = [a.get("agent_id") for a in (crew.agents or []) if a.get("agent_id")]
        experts = self.db.query(ExpertAgent).filter(ExpertAgent.id.in_(agent_ids)).all()
        expert_map = {str(e.id): e for e in experts}

        # Transition: queued -> running
        await self._transition_run(run, RunStatus.running, "Starting crew execution", mission)
        run.started_at = datetime.now(UTC)
        self.db.commit()

        # Update mission status
        mission.status = MissionStatus.running
        mission.started_at = datetime.now(UTC)
        self.db.commit()

        expert_names = [e.name for e in experts]
        await emit_crew_run_started(self.db, mission.id, run.id, crew.id, expert_names)
        self.db.commit()

        start_time = time.time()
        all_findings: list[Finding] = []
        total_tokens = 0
        total_cost = 0.0
        storm_outline = None
        storm_status = "skipped"
        storm_fallback_reason: str | None = None

        # ── STORM PHASE 0 (pre-write) ───────────────────────────────
        # Runs before Scout when AGENTARY_STORM_ENABLED=true or the
        # mission has storm_enabled=True. Failure falls back silently to
        # the legacy DeerFlow pipeline; telemetry is emitted either way.
        try:
            from ..storm import run_storm_prewrite, should_run_storm
            from ..storm.telemetry import record_storm_run

            if should_run_storm(mission):
                storm_step = self._record_step(
                    run_id=run.id,
                    run_type="crew",
                    step_type=StepType.synthesis,
                    step_name="STORM Phase 0: outline-first pre-writing",
                    status="running",
                )
                self.db.commit()
                try:
                    storm_outline = await run_storm_prewrite(mission, self.db)
                    if storm_outline is None:
                        storm_status = "fallback"
                        storm_fallback_reason = "pre_write_returned_none"
                        storm_step.status = "completed"
                    else:
                        storm_status = "completed"
                        storm_step.status = "completed"
                except Exception as exc:
                    storm_status = "error"
                    storm_fallback_reason = f"{type(exc).__name__}: {exc}"[:200]
                    logger.warning("STORM pre-write failed for mission %s: %s", mission.id, exc)
                    storm_step.status = "failed"
                    storm_step.error_message = storm_fallback_reason
                storm_step.completed_at = datetime.now(UTC)
                self.db.commit()

                # Telemetry — best effort, never raises
                try:
                    record_storm_run(
                        db=self.db,
                        mission_id=mission.id,
                        crew_run_id=run.id,
                        outline=storm_outline,
                        report=None,
                        status=storm_status,
                        fallback_reason=storm_fallback_reason,
                        budget=None,
                        duration_ms=int((time.time() - start_time) * 1000),
                        extra_meta={"phase": "pre_write"},
                    )
                except Exception as exc:
                    logger.debug("record_storm_run failed (non-fatal): %s", exc)
        except ImportError:
            # STORM package missing — proceed with legacy flow silently
            pass

        try:
            # Separate phases (DeerFlow methodology)
            scout_tasks = [t for t in run.tasks if t.task_type == "scout"]
            research_tasks = [
                t
                for t in run.tasks
                if t.task_type not in ("scout", "synthesis", "report_writing", "gap_check")
            ]
            gap_check_tasks = [t for t in run.tasks if t.task_type == "gap_check"]
            synthesis_tasks = [t for t in run.tasks if t.task_type == "synthesis"]
            report_tasks = [t for t in run.tasks if t.task_type == "report_writing"]

            # ── SCOUT PHASE (DeerFlow Phase 1) ──────────────────────
            if scout_tasks:
                scout_step = self._record_step(
                    run_id=run.id,
                    run_type="crew",
                    step_type=StepType.searching,
                    step_name="DeerFlow Scout: broad exploration",
                    status="running",
                )
                self.db.commit()
                scout_start = time.time()

                for task in scout_tasks:
                    result = await self._execute_expert_task_safe(
                        task, expert_map, mission, run, crew
                    )
                    if isinstance(result, tuple):
                        findings, tokens, cost = result
                        all_findings.extend(findings)
                        total_tokens += tokens
                        total_cost += cost

                scout_step.status = "completed"
                scout_step.duration_ms = int((time.time() - scout_start) * 1000)
                scout_step.completed_at = datetime.now(UTC)
                self.db.commit()

            # ── PARALLEL RESEARCH PHASE (DeerFlow Phase 2) ──────────
            if research_tasks:
                results = await asyncio.gather(
                    *[
                        self._execute_expert_task_safe(task, expert_map, mission, run, crew)
                        for task in research_tasks
                    ],
                    return_exceptions=True,
                )
                failed_count = 0
                failed_errors: list[str] = []
                for i, result in enumerate(results):
                    if isinstance(result, tuple):
                        findings, tokens, cost = result
                        all_findings.extend(findings)
                        total_tokens += tokens
                        total_cost += cost
                    elif isinstance(result, Exception):
                        failed_count += 1
                        error_msg = str(result)
                        failed_errors.append(error_msg)

                        # Mark the task as failed with failure category
                        task_obj = research_tasks[i]
                        task_obj.status = "failed"
                        task_obj.error_message = error_msg[:2000]
                        if isinstance(result, asyncio.TimeoutError):
                            task_obj.failure_category = FailureCategory.timeout
                        self.db.commit()

                        await emit_expert_thinking(
                            self.db,
                            mission.id,
                            run.id,
                            crew.id,
                            None,
                            "System",
                            "\u26a0\ufe0f",
                            f"Research task failed: {error_msg[:200]}",
                            "error",
                        )
                        self.db.commit()

                # If ALL research tasks failed, abort the run
                if research_tasks and failed_count == len(research_tasks):
                    raise RuntimeError(
                        f"All {failed_count} research tasks failed: {'; '.join(failed_errors[:3])}"
                    )

            # ── GAP CHECK PHASE (DeerFlow Phase 3) ─────────────────
            if gap_check_tasks and all_findings:
                gap_step = self._record_step(
                    run_id=run.id,
                    run_type="crew",
                    step_type=StepType.analyzing,
                    step_name="DeerFlow Gap Check: audit completeness",
                    status="running",
                )
                self.db.commit()
                gap_start = time.time()

                for task in gap_check_tasks:
                    expert = expert_map.get(str(task.expert_agent_id))
                    if not expert:
                        continue

                    # Feed all findings to gap checker
                    findings_summary = self._summarize_findings(all_findings)
                    task.input_data = {
                        **(task.input_data or {}),
                        "findings_summary": findings_summary,
                        "mission_name": mission.name,
                        "mission_objective": mission.objective or "",
                        "gap_check_criteria": (
                            "Audit against 6 DeerFlow diversity categories: "
                            "1) Facts & Data, 2) Examples & Cases, "
                            "3) Expert Opinions, 4) Trends & Predictions, "
                            "5) Comparisons, 6) Challenges & Criticisms. "
                            "Report which categories are well-covered and which have gaps."
                        ),
                    }
                    self.db.commit()

                    result = await self._execute_expert_task_safe(
                        task, expert_map, mission, run, crew
                    )
                    if isinstance(result, tuple):
                        findings, tokens, cost = result
                        all_findings.extend(findings)
                        total_tokens += tokens
                        total_cost += cost

                gap_step.status = "completed"
                gap_step.duration_ms = int((time.time() - gap_start) * 1000)
                gap_step.completed_at = datetime.now(UTC)
                self.db.commit()

            # ── SYNTHESIS PHASE (DeerFlow Phase 4) ──────────────────
            if synthesis_tasks:
                synth_phase_step = self._record_step(
                    run_id=run.id,
                    run_type="crew",
                    step_type=StepType.synthesis,
                    step_name="Synthesis phase",
                    status="running",
                )
                self.db.commit()
                synth_start = time.time()

            for task in synthesis_tasks:
                expert = expert_map.get(str(task.expert_agent_id))
                if not expert:
                    continue

                # Feed all findings to synthesizer
                findings_summary = self._summarize_findings(all_findings)
                task.input_data = {
                    **(task.input_data or {}),
                    "findings_summary": findings_summary,
                    "mission_name": mission.name,
                    "mission_objective": mission.objective or "",
                }
                self.db.commit()

                result = await self._execute_expert_task(task, expert_map, mission, run, crew)
                if isinstance(result, tuple):
                    findings, tokens, cost = result
                    all_findings.extend(findings)
                    total_tokens += tokens
                    total_cost += cost

            if synthesis_tasks:
                synth_phase_step.status = "completed"
                synth_phase_step.duration_ms = int((time.time() - synth_start) * 1000)
                synth_phase_step.completed_at = datetime.now(UTC)
                self.db.commit()

            # ── REPORT PHASE ─────────────────────────────────────────
            if report_tasks:
                report_phase_step = self._record_step(
                    run_id=run.id,
                    run_type="crew",
                    step_type=StepType.synthesis,
                    step_name="Report phase",
                    status="running",
                )
                self.db.commit()
                report_phase_start = time.time()

            for task in report_tasks:
                expert = expert_map.get(str(task.expert_agent_id))
                if not expert:
                    continue

                findings_summary = self._summarize_findings(all_findings)
                task.input_data = {
                    **(task.input_data or {}),
                    "all_findings": findings_summary,
                    "mission_name": mission.name,
                    "mission_objective": mission.objective or "",
                }
                self.db.commit()

                result = await self._execute_expert_task(task, expert_map, mission, run, crew)
                if isinstance(result, tuple):
                    findings, tokens, cost = result
                    total_tokens += tokens
                    total_cost += cost

                    # Store report data in task output for later report generation

            if report_tasks:
                report_phase_step.status = "completed"
                report_phase_step.duration_ms = int((time.time() - report_phase_start) * 1000)
                report_phase_step.completed_at = datetime.now(UTC)
                self.db.commit()

            # ── FINALIZE ─────────────────────────────────────────────
            elapsed = time.time() - start_time

            # Determine if we should use partially_failed
            failed_task_count = sum(
                1
                for t in run.tasks
                if (t.status.value if hasattr(t.status, "value") else str(t.status)) == "failed"
            )
            total_task_count = len(run.tasks) if run.tasks else 0

            if failed_task_count > 0 and failed_task_count < total_task_count:
                await self._transition_run(
                    run,
                    RunStatus.partially_failed,
                    f"{failed_task_count}/{total_task_count} tasks failed",
                    mission,
                )
                # Resolve partial failure to completed since we do have findings
                if all_findings:
                    await self._transition_run(
                        run,
                        RunStatus.completed,
                        "Resolved: partial results available",
                        mission,
                    )
                else:
                    await self._transition_run(
                        run,
                        RunStatus.failed,
                        "Resolved: no findings despite partial execution",
                        mission,
                    )
            else:
                await self._transition_run(
                    run,
                    RunStatus.completed,
                    f"Completed with {len(all_findings)} findings",
                    mission,
                )

            run.completed_at = datetime.now(UTC)
            run.duration_seconds = elapsed
            run.summary = f"Completed with {len(all_findings)} findings from {len(experts)} experts"
            run.metrics = {
                "findings_count": len(all_findings),
                "sources_queried": len({f.source_url for f in all_findings if f.source_url}),
                "tokens_used": total_tokens,
                "cost_usd": round(total_cost, 4),
                "experts_used": len(experts),
            }

            run_status_str = run.status.value if hasattr(run.status, "value") else str(run.status)
            mission.status = (
                MissionStatus.completed if run_status_str == "completed" else MissionStatus.failed
            )
            mission.completed_at = datetime.now(UTC)
            mission.findings_count = len(all_findings)
            mission.confidence_score = (
                sum(f.confidence for f in all_findings) / len(all_findings) if all_findings else 0.0
            )
            mission.summary = run.summary

            await emit_crew_run_completed(self.db, mission.id, run.id, crew.id, len(all_findings))
            self.db.commit()

        except Exception as e:
            # Categorize failure
            failure_cat = FailureCategory.internal
            err_msg = str(e)
            err_type = type(e).__name__
            if "rate" in err_msg.lower() or "429" in err_msg:
                failure_cat = FailureCategory.rate_limited
            elif "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
                failure_cat = FailureCategory.timeout
            elif "api" in err_type.lower() or "google" in err_type.lower():
                failure_cat = FailureCategory.model_error

            run.failure_category = failure_cat
            run.failure_message = err_msg
            run.error = {"message": err_msg, "type": err_type}
            run.completed_at = datetime.now(UTC)
            run.duration_seconds = time.time() - start_time

            try:
                await self._transition_run(run, RunStatus.failed, err_msg, mission)
            except InvalidTransition:
                current_status = run.status if isinstance(run.status, str) else run.status.value
                run.status = "failed"
                transitions = list(run.state_transitions or [])
                transitions.append(
                    {
                        "from": current_status,
                        "to": "failed",
                        "timestamp": datetime.now(UTC).isoformat(),
                        "reason": "InvalidTransition fallback — forced to failed",
                    }
                )
                run.state_transitions = transitions
                self.db.commit()

            mission.status = MissionStatus.failed
            self.db.commit()
            raise

        return run

    async def _execute_expert_task_safe(
        self,
        task: CrewTask,
        expert_map: dict[str, ExpertAgent],
        mission: Mission,
        run: CrewRun,
        crew: AgentCrew,
        timeout_seconds: float = _TASK_TIMEOUT_SECONDS,
    ) -> tuple[list[Finding], int, float]:
        """Wrapper that adds a per-task timeout and catches exceptions.

        Returns the same tuple as _execute_expert_task on success.
        Raises on timeout or unrecoverable error so asyncio.gather
        can capture it via return_exceptions=True.
        """
        try:
            return await asyncio.wait_for(
                self._execute_expert_task(task, expert_map, mission, run, crew),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            expert = expert_map.get(str(task.expert_agent_id))
            expert_name = expert.name if expert else "Unknown"
            logger.error(
                "Expert task timed out after %.0fs: expert=%s task_type=%s",
                timeout_seconds,
                expert_name,
                task.task_type,
            )
            task.status = "failed"
            task.error_message = f"Task timed out after {timeout_seconds}s"
            self.db.commit()
            raise
        except Exception as exc:
            logger.error(
                "Expert task failed with unexpected error: %s",
                exc,
                exc_info=True,
            )
            raise

    async def _execute_expert_task(
        self,
        task: CrewTask,
        expert_map: dict[str, ExpertAgent],
        mission: Mission,
        run: CrewRun,
        crew: AgentCrew,
    ) -> tuple[list[Finding], int, float]:
        """Execute a single expert's task with an agentic tool-calling loop."""
        expert = expert_map.get(str(task.expert_agent_id))
        if not expert:
            task.status = "failed"
            task.error_message = "Expert agent not found"
            self.db.commit()
            return [], 0, 0.0

        expert_icon = expert.icon or "\U0001f916"
        expert_tools = expert.tools if isinstance(expert.tools, list) else []
        model_config = expert.model_config_json or {}
        model_name = model_config.get("model", _DEFAULT_MODEL)
        temperature = model_config.get("temperature", 0.3)

        # Mark task as running
        task.status = "running"
        task.started_at = datetime.now(UTC)
        task.thinking_log = []
        self.db.commit()

        await emit_task_started(
            self.db,
            mission.id,
            run.id,
            crew.id,
            expert.id,
            expert.name,
            task.task_type,
        )
        self.db.commit()

        # Record RunStep: expert task started
        task_step = self._record_step(
            run_id=run.id,
            run_type="crew",
            step_type=StepType.expert_task,
            step_name=f"{expert.name}: {task.task_type}",
            status="running",
            input_summary=_truncate(task.input_data, 2000),
        )
        self.db.commit()

        start_time = time.time()
        total_tokens = 0
        findings: list[Finding] = []

        try:
            # Build initial messages
            system_prompt = expert.system_prompt or "You are a helpful research assistant."
            user_prompt = self._build_task_prompt(task, mission)

            messages = [{"role": "user", "parts": [{"text": user_prompt}]}]

            # Get tool declarations for Gemini
            tool_declarations = tool_registry.get_gemini_tool_declarations(expert_tools)

            # ── AGENTIC TOOL-CALLING LOOP ────────────────────────────
            max_iterations = _MAX_TOOL_ITERATIONS
            done = False
            iteration = 0

            client = get_client()

            while not done and iteration < max_iterations:
                iteration += 1

                # Generate response with tools
                config_kwargs: dict[str, Any] = {
                    "system_instruction": system_prompt,
                    "temperature": temperature,
                    "http_options": {"timeout": _API_TIMEOUT_MS},
                }

                tools_param = None
                if tool_declarations:
                    tools_param = [
                        types.Tool(
                            function_declarations=[
                                types.FunctionDeclaration(
                                    name=td["name"],
                                    description=td["description"],
                                    parameters=td.get("parameters"),
                                )
                                for td in tool_declarations
                            ]
                        )
                    ]
                    config_kwargs["tools"] = tools_param

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    functools.partial(
                        client.models.generate_content,
                        model=model_name,
                        contents=messages,
                        config=types.GenerateContentConfig(**config_kwargs),
                    ),
                )

                # Check for function calls
                has_function_call = False
                if response.candidates and response.candidates[0].content:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            has_function_call = True
                            fc = part.function_call
                            tool_name = fc.name
                            tool_args = dict(fc.args) if fc.args else {}

                            # Emit thinking event
                            thought = f"Using {tool_name}"
                            if tool_name in ("gemini_search", "exa_search"):
                                thought = f'Searching: "{tool_args.get("query", "")}"'
                            elif tool_name == "web_scraper":
                                thought = f'Scraping: {tool_args.get("url", "")[:60]}'
                            elif tool_name == "voice_caller":
                                thought = f'Calling: {tool_args.get("business_name", "")}'
                            elif tool_name == "python_executor":
                                thought = "Running data analysis..."
                            elif tool_name == "chart_generator":
                                thought = f'Generating chart: {tool_args.get("title", "")}'

                            action = "searching" if "search" in tool_name else "analyzing"
                            if tool_name == "web_scraper":
                                action = "scraping"
                            elif tool_name == "voice_caller":
                                action = "calling"

                            await emit_expert_thinking(
                                self.db,
                                mission.id,
                                run.id,
                                crew.id,
                                expert.id,
                                expert.name,
                                expert_icon,
                                thought,
                                action,
                                tool_name,
                            )
                            self.db.commit()

                            # Execute tool
                            tool_start = time.time()
                            tool_result = await tool_registry.execute(tool_name, **tool_args)
                            tool_elapsed_ms = int((time.time() - tool_start) * 1000)

                            # Record RunStep: tool call
                            self._record_step(
                                run_id=run.id,
                                run_type="crew",
                                step_type=StepType.tool_call,
                                step_name=f"tool:{tool_name}",
                                status="completed",
                                input_summary=_truncate(tool_args, 2000),
                                output_summary=_truncate(
                                    (
                                        tool_result
                                        if isinstance(tool_result, dict)
                                        else {"result": str(tool_result)[:2000]}
                                    ),
                                    5000,
                                ),
                                duration_ms=tool_elapsed_ms,
                                parent_step_id=task_step.id,
                            )
                            self.db.commit()

                            # Add thinking log entry
                            log_entry = {
                                "timestamp": datetime.now(UTC).isoformat(),
                                "thought": thought,
                                "action": action,
                                "tool": tool_name,
                                "result_preview": json.dumps(tool_result)[:200],
                            }
                            thinking_log = list(task.thinking_log or [])
                            thinking_log.append(log_entry)
                            task.thinking_log = thinking_log
                            self.db.commit()

                            # Append tool result to messages
                            messages.append({"role": "model", "parts": [part]})
                            messages.append(
                                {
                                    "role": "user",
                                    "parts": [
                                        types.Part.from_function_response(
                                            name=tool_name,
                                            response={"result": json.dumps(tool_result)[:4000]},
                                        )
                                    ],
                                }
                            )
                            break  # Process one function call at a time

                if not has_function_call:
                    # Final text response — parse findings
                    response_text = response.text if response.text else ""

                    await emit_expert_thinking(
                        self.db,
                        mission.id,
                        run.id,
                        crew.id,
                        expert.id,
                        expert.name,
                        expert_icon,
                        "Compiling findings...",
                        "writing",
                    )
                    self.db.commit()

                    # Parse findings from response
                    parsed = self._parse_findings(response_text, expert, task, mission)
                    for f_data in parsed:
                        # Map category string to FindingType enum
                        raw_type = f_data.get("category", f_data.get("finding_type", "data_point"))
                        try:
                            finding_type = FindingType(raw_type)
                        except ValueError:
                            finding_type = FindingType.data_point

                        # Map source_type string to SourceType enum
                        raw_source = f_data.get("source_type", "web")
                        try:
                            source_type = SourceType(raw_source)
                        except ValueError:
                            source_type = SourceType.web

                        finding = Finding(
                            id=uuid.uuid4(),
                            project_id=mission.project_id,
                            mission_id=mission.id,
                            expert_agent_id=expert.id,
                            finding_type=finding_type,
                            title=f_data.get("title", "Untitled finding")[:500],
                            content=f_data.get("content", ""),
                            structured_data=f_data.get("structured_data"),
                            source_type=source_type,
                            source_url=f_data.get("source_url"),
                            source_name=f_data.get("source_name"),
                            confidence=float(f_data.get("confidence", 0.5)),
                            tags=f_data.get("tags", []),
                        )
                        self.db.add(finding)
                        self.db.flush()
                        findings.append(finding)

                        await emit_finding_added(
                            self.db,
                            mission.id,
                            run.id,
                            finding.title,
                            finding.confidence,
                            finding.source_name,
                        )

                        # Emit signal for the intelligence pipeline
                        try:
                            signal_svc = SignalService(self.db)
                            signal_svc.create_signal(
                                project_id=mission.project_id,
                                user_id=mission.user_id,
                                source_type=SignalSourceType.mission,
                                signal_type=SignalType.data_extracted,
                                title=f"Finding: {finding.title}",
                                content=finding.content,
                                structured_data=finding.structured_data or {},
                                source_id=run.id,
                                entity_id=None,
                                confidence=finding.confidence,
                            )
                        except Exception:
                            logger.debug("Signal emission failed for finding %s", finding.id)

                    # Store raw output
                    task.output_data = {
                        "response_text": response_text[:5000],
                        "findings_count": len(parsed),
                    }
                    done = True

                # Estimate tokens (rough)
                total_tokens += len(str(messages[-1])) // 4

            # Finalize task
            elapsed = time.time() - start_time
            cost = total_tokens * _TOKEN_COST_PER_TOKEN  # Rough estimate
            task.status = "completed"
            task.completed_at = datetime.now(UTC)
            task.duration_seconds = elapsed
            task.findings_count = len(findings)
            self.db.commit()

            await emit_task_completed(
                self.db,
                mission.id,
                run.id,
                crew.id,
                expert.id,
                expert.name,
                task.task_type,
                len(findings),
            )

            # Update RunStep: expert task completed
            task_step.status = "completed"
            task_step.tokens_used = total_tokens
            task_step.cost_usd = cost
            task_step.duration_ms = int(elapsed * 1000)
            task_step.output_summary = _truncate(
                {"findings_count": len(findings)},
                5000,
            )
            task_step.completed_at = datetime.now(UTC)
            self.db.commit()

            return findings, total_tokens, cost

        except Exception as e:
            logger.exception("Expert task failed for agent %s", task.expert_agent_id)
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now(UTC)
            task.duration_seconds = time.time() - start_time

            # Update RunStep: expert task failed
            task_step.status = "failed"
            task_step.error = {"message": str(e)[:2000], "type": type(e).__name__}
            task_step.duration_ms = int((time.time() - start_time) * 1000)
            task_step.completed_at = datetime.now(UTC)
            self.db.commit()
            raise  # Let gather() capture it as an Exception instance

    def _build_task_prompt(self, task: CrewTask, mission: Mission) -> str:
        """Build the user prompt for an expert task."""
        parts = [
            f"## Mission: {mission.name}",
            f"Objective: {mission.objective or mission.description or 'Research this topic thoroughly'}",
        ]
        if mission.parameters:
            parts.append(f"Parameters: {json.dumps(mission.parameters)}")
        parts.append(f"\n## Your Task\n{task.description}")
        if task.input_data:
            parts.append(f"\n## Input Data\n{json.dumps(task.input_data, indent=2)}")
        parts.append(
            "\n## Instructions\n"
            "1. Use your available tools to gather information.\n"
            "2. After gathering sufficient data, return your findings as a JSON array.\n"
            "3. Each finding must have: title, content, category, confidence (0-1), "
            "source_url, source_name, tags.\n"
            "4. Return ONLY the JSON array of findings in your final response."
        )
        return "\n".join(parts)

    def _parse_findings(
        self,
        response_text: str,
        expert: ExpertAgent,
        task: CrewTask,
        mission: Mission,
    ) -> list[dict[str, Any]]:
        """Parse findings from expert's text response."""
        # Try to extract JSON array
        text = response_text.strip()

        # Strip markdown fences
        if "```json" in text:
            text = text.split("```json", 1)[-1]
        if "```" in text:
            text = text.split("```")[0]
        text = text.strip()

        # Try parsing as JSON
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                # Could be wrapped: {"findings": [...]} or {"key_findings": [...]}
                for key in ("findings", "key_findings", "results", "data"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                return [data]
        except json.JSONDecodeError:
            pass

        # Try to find JSON array in text
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass

        # Fallback: create a single finding from the text
        if text:
            return [
                {
                    "title": f"{expert.name} analysis",
                    "content": text[:2000],
                    "category": "insight",
                    "confidence": 0.5,
                    "source_type": "inference",
                    "tags": [],
                }
            ]

        return []

    def _summarize_findings(self, findings: list[Finding]) -> str:
        """Create a text summary of all findings for synthesizer/report writer."""
        parts = []
        for i, f in enumerate(findings, 1):
            finding_kind = (
                f.finding_type.value if hasattr(f.finding_type, "value") else str(f.finding_type)
            )
            parts.append(
                f"{i}. [{finding_kind}] {f.title} (confidence: {(f.confidence or 0):.0%})\n"
                f"   {f.content[:300]}\n"
                f"   Source: {f.source_name or 'N/A'} | {f.source_url or 'N/A'}"
            )
        return "\n\n".join(parts) if parts else "No findings yet."
