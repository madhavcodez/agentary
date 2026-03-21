"""CrewRunner — THE EXECUTION ENGINE for expert agent crews."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from ...models.agent_crew import AgentCrew
from ...models.crew_run import CrewRun
from ...models.crew_task import CrewTask
from ...models.expert_agent import ExpertAgent
from ...models.finding import Finding
from ...models.mission import Mission, MissionStatus
from ...models.mission_research_result import MissionResearchResult
from ..gemini import generate_text, get_client
from .events import (
    emit_crew_run_completed,
    emit_crew_run_started,
    emit_expert_thinking,
    emit_finding_added,
    emit_task_completed,
    emit_task_started,
)
from .tool_registry import tool_registry


class CrewRunner:
    """Executes a crew run with parallel expert research and agentic tool-calling loops."""

    def __init__(self, db: Session) -> None:
        self.db = db

    async def execute_run(self, run_id: uuid.UUID) -> CrewRun:
        """Main execution entry point.

        1. Load run, crew, mission, experts
        2. Emit CREW_RUN_STARTED
        3. Separate researchers from synthesizer/report_writer
        4. PARALLEL PHASE: All researchers execute simultaneously
        5. SYNTHESIS PHASE: Synthesizer receives all findings
        6. REPORT PHASE: ReportWriter generates structured output
        7. Emit CREW_RUN_COMPLETED
        """
        run = self.db.query(CrewRun).filter_by(id=run_id).first()
        if not run:
            raise ValueError(f"CrewRun {run_id} not found")

        crew = self.db.query(AgentCrew).filter_by(id=run.crew_id).first()
        mission = self.db.query(Mission).filter_by(id=run.mission_id).first()

        if not crew or not mission:
            run.status = "failed"
            run.error = {"message": "Crew or mission not found"}
            self.db.commit()
            raise ValueError("Crew or mission not found")

        # Load experts from crew.agents JSONB
        agent_ids = [a.get("agent_id") for a in (crew.agents or []) if a.get("agent_id")]
        experts = (
            self.db.query(ExpertAgent)
            .filter(ExpertAgent.id.in_(agent_ids))
            .all()
        )
        expert_map = {str(e.id): e for e in experts}

        # Update run status
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        self.db.commit()

        # Update mission status
        mission.status = MissionStatus.running
        mission.started_at = datetime.now(timezone.utc)
        self.db.commit()

        expert_names = [e.name for e in experts]
        await emit_crew_run_started(
            self.db, mission.id, run.id, crew.id, expert_names
        )
        self.db.commit()

        start_time = time.time()
        all_findings: list[Finding] = []
        total_tokens = 0
        total_cost = 0.0

        try:
            # Separate phases
            research_tasks = [
                t for t in run.tasks
                if t.task_type not in ("synthesis", "report_writing")
            ]
            synthesis_tasks = [t for t in run.tasks if t.task_type == "synthesis"]
            report_tasks = [t for t in run.tasks if t.task_type == "report_writing"]

            # ── PARALLEL RESEARCH PHASE ──────────────────────────────
            if research_tasks:
                results = await asyncio.gather(
                    *[
                        self._execute_expert_task(task, expert_map, mission, run, crew)
                        for task in research_tasks
                    ],
                    return_exceptions=True,
                )
                for result in results:
                    if isinstance(result, tuple):
                        findings, tokens, cost = result
                        all_findings.extend(findings)
                        total_tokens += tokens
                        total_cost += cost
                    elif isinstance(result, Exception):
                        await emit_expert_thinking(
                            self.db, mission.id, run.id, crew.id,
                            None, "System", "\u26a0\ufe0f",
                            f"Research task failed: {result}", "error",
                        )
                        self.db.commit()

            # ── SYNTHESIS PHASE ──────────────────────────────────────
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

                result = await self._execute_expert_task(
                    task, expert_map, mission, run, crew
                )
                if isinstance(result, tuple):
                    findings, tokens, cost = result
                    all_findings.extend(findings)
                    total_tokens += tokens
                    total_cost += cost

            # ── REPORT PHASE ─────────────────────────────────────────
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

                result = await self._execute_expert_task(
                    task, expert_map, mission, run, crew
                )
                if isinstance(result, tuple):
                    findings, tokens, cost = result
                    total_tokens += tokens
                    total_cost += cost

                    # Create MissionResearchResult from report output
                    if task.output_data:
                        research_result = MissionResearchResult(
                            id=uuid.uuid4(),
                            mission_id=mission.id,
                            crew_run_id=run.id,
                            title=task.output_data.get("title", f"Report: {mission.name}"),
                            summary=task.output_data.get("summary", ""),
                            sections=task.output_data.get("sections", []),
                            methodology=task.output_data.get("methodology", ""),
                            sources_used=task.output_data.get("sources_used", len(all_findings)),
                            findings_count=len(all_findings),
                            confidence=task.output_data.get("confidence", 0.5),
                        )
                        self.db.add(research_result)

            # ── FINALIZE ─────────────────────────────────────────────
            elapsed = time.time() - start_time
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.duration_seconds = elapsed
            run.summary = f"Completed with {len(all_findings)} findings from {len(experts)} experts"
            run.metrics = {
                "findings_count": len(all_findings),
                "sources_queried": len({f.source_url for f in all_findings if f.source_url}),
                "tokens_used": total_tokens,
                "cost_usd": round(total_cost, 4),
                "experts_used": len(experts),
            }

            mission.status = MissionStatus.completed
            mission.completed_at = datetime.now(timezone.utc)
            mission.findings_count = len(all_findings)
            mission.confidence_score = (
                sum(f.confidence for f in all_findings) / len(all_findings)
                if all_findings else 0.0
            )
            mission.summary = run.summary

            await emit_crew_run_completed(
                self.db, mission.id, run.id, crew.id, len(all_findings)
            )
            self.db.commit()

        except Exception as e:
            run.status = "failed"
            run.error = {"message": str(e), "type": type(e).__name__}
            run.completed_at = datetime.now(timezone.utc)
            run.duration_seconds = time.time() - start_time
            mission.status = MissionStatus.failed
            self.db.commit()
            raise

        return run

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
        model_name = model_config.get("model", "gemini-2.5-flash")
        temperature = model_config.get("temperature", 0.3)

        # Mark task as running
        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        task.thinking_log = []
        self.db.commit()

        await emit_task_started(
            self.db, mission.id, run.id, crew.id,
            expert.id, expert.name, task.task_type,
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
            max_iterations = 10
            done = False
            iteration = 0

            client = get_client()

            while not done and iteration < max_iterations:
                iteration += 1

                # Generate response with tools
                config_kwargs: dict[str, Any] = {
                    "system_instruction": system_prompt,
                    "temperature": temperature,
                }

                tools_param = None
                if tool_declarations:
                    from google.genai import types
                    tools_param = [types.Tool(function_declarations=[
                        types.FunctionDeclaration(
                            name=td["name"],
                            description=td["description"],
                            parameters=td.get("parameters"),
                        )
                        for td in tool_declarations
                    ])]

                response = client.models.generate_content(
                    model=model_name,
                    contents=messages,
                    config=types.GenerateContentConfig(**config_kwargs),
                    tools=tools_param,
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
                                self.db, mission.id, run.id, crew.id,
                                expert.id, expert.name, expert_icon,
                                thought, action, tool_name,
                            )
                            self.db.commit()

                            # Execute tool
                            tool_result = await tool_registry.execute(tool_name, **tool_args)

                            # Add thinking log entry
                            log_entry = {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
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
                            from google.genai import types as gtypes
                            messages.append({
                                "role": "user",
                                "parts": [gtypes.Part.from_function_response(
                                    name=tool_name,
                                    response={"result": json.dumps(tool_result)[:4000]},
                                )],
                            })
                            break  # Process one function call at a time

                if not has_function_call:
                    # Final text response — parse findings
                    response_text = response.text if response.text else ""

                    await emit_expert_thinking(
                        self.db, mission.id, run.id, crew.id,
                        expert.id, expert.name, expert_icon,
                        "Compiling findings...", "writing",
                    )
                    self.db.commit()

                    # Parse findings from response
                    parsed = self._parse_findings(response_text, expert, task, mission)
                    for f_data in parsed:
                        finding = Finding(
                            id=uuid.uuid4(),
                            mission_id=mission.id,
                            crew_task_id=task.id,
                            expert_agent_id=expert.id,
                            category=f_data.get("category", "data_point"),
                            title=f_data.get("title", "Untitled finding"),
                            content=f_data.get("content", ""),
                            structured_data=f_data.get("structured_data"),
                            source_type=f_data.get("source_type", "web"),
                            source_url=f_data.get("source_url"),
                            source_name=f_data.get("source_name"),
                            confidence=float(f_data.get("confidence", 0.5)),
                            tags=f_data.get("tags", []),
                        )
                        self.db.add(finding)
                        findings.append(finding)

                        await emit_finding_added(
                            self.db, mission.id, run.id,
                            finding.title, finding.confidence, finding.source_name,
                        )

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
            task.status = "completed"
            task.completed_at = datetime.now(timezone.utc)
            task.duration_seconds = elapsed
            task.findings_produced = len(findings)
            task.tokens_used = total_tokens
            task.cost_usd = total_tokens * 0.000001  # Rough estimate
            self.db.commit()

            await emit_task_completed(
                self.db, mission.id, run.id, crew.id,
                expert.id, expert.name, task.task_type, len(findings),
            )
            self.db.commit()

            return findings, total_tokens, task.cost_usd

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.now(timezone.utc)
            task.duration_seconds = time.time() - start_time
            self.db.commit()
            return findings, total_tokens, 0.0

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
            return [{
                "title": f"{expert.name} analysis",
                "content": text[:2000],
                "category": "insight",
                "confidence": 0.5,
                "source_type": "inference",
                "tags": [],
            }]

        return []

    def _summarize_findings(self, findings: list[Finding]) -> str:
        """Create a text summary of all findings for synthesizer/report writer."""
        parts = []
        for i, f in enumerate(findings, 1):
            parts.append(
                f"{i}. [{f.category}] {f.title} (confidence: {f.confidence:.0%})\n"
                f"   {f.content[:300]}\n"
                f"   Source: {f.source_name or 'N/A'} | {f.source_url or 'N/A'}"
            )
        return "\n\n".join(parts) if parts else "No findings yet."
