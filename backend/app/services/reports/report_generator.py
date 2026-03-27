import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import markdown2

from google import genai
from sqlalchemy.orm import Session

from ...config import settings
from ...core.events import Event, EventType, event_bus
from ...models.enums import FailureCategory
from ...models.finding import Finding
from ...models.mission import Mission
from ...models.crew_run import CrewRun
from ...models.report import Report
from .chart_generator import ChartGenerator

logger = logging.getLogger(__name__)

_REPORT_MODEL = "gemini-2.5-flash"


def _append_report_transition(
    report: Report,
    from_state: str,
    to_state: str,
    reason: str | None = None,
) -> None:
    """Append a state transition record to a Report."""
    record = {
        "from": from_state,
        "to": to_state,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
    }
    transitions = list(report.state_transitions or [])
    transitions.append(record)
    report.state_transitions = transitions

TEMPLATES_DIR = Path(__file__).parent / "templates"

MARKDOWN2_EXTRAS = [
    "tables",
    "fenced-code-blocks",
    "header-ids",
    "strike",
    "task_list",
]


class ReportGenerator:
    """Generates polished research reports from mission findings using Gemini."""

    def __init__(self):
        self.chart_gen = ChartGenerator()
        self._client = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=settings.gemini_api_key)
        return self._client

    # ------------------------------------------------------------------
    # Template helpers
    # ------------------------------------------------------------------

    def _load_template(self, report_type: str) -> dict:
        """Load report template JSON by type, falling back to research_report."""
        path = TEMPLATES_DIR / f"{report_type}.json"
        if not path.exists():
            path = TEMPLATES_DIR / "research_report.json"
        with open(path) as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Gemini wrapper
    # ------------------------------------------------------------------

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini and return the text response.

        Raises on API errors so callers can handle them.
        """
        response = self.client.models.generate_content(
            model=_REPORT_MODEL,
            contents=prompt,
        )
        return response.text

    # ------------------------------------------------------------------
    # Finding formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_findings_for_prompt(findings: list[Finding]) -> str:
        """Render a list of Finding objects into a numbered text block for prompts."""
        parts: list[str] = []
        for idx, f in enumerate(findings, start=1):
            lines = [
                f"### Finding {idx}: {f.title}",
                f"Category: {getattr(f, 'category', None) or getattr(f, 'finding_type', 'unknown')}",
                f"Confidence: {f.confidence:.0%}",
                f"Verified: {'Yes' if f.verified else 'No'}",
            ]
            if f.source_name:
                lines.append(f"Source: {f.source_name}")
            if f.source_url:
                lines.append(f"URL: {f.source_url}")
            if f.tags:
                lines.append(f"Tags: {', '.join(f.tags)}")
            lines.append(f"\n{f.content}")
            if f.structured_data:
                lines.append(f"\nStructured data: {json.dumps(f.structured_data, default=str)}")
            parts.append("\n".join(lines))
        return "\n\n---\n\n".join(parts)

    # ------------------------------------------------------------------
    # Structured-data aggregation
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_structured_data(findings: list[Finding]) -> dict:
        """Merge structured_data from all findings into one dict keyed by category."""
        aggregated: dict = {}
        for f in findings:
            if not f.structured_data:
                continue
            category = f.category or "general"
            aggregated.setdefault(category, []).append(
                {
                    "finding_id": str(f.id),
                    "title": f.title,
                    "data": f.structured_data,
                }
            )
        return aggregated

    # ------------------------------------------------------------------
    # Source compilation
    # ------------------------------------------------------------------

    @staticmethod
    def _compile_sources(findings: list[Finding]) -> list[dict]:
        """Deduplicate and compile a source list from findings."""
        seen_urls: set[str] = set()
        sources: list[dict] = []
        for f in findings:
            if not f.source_name and not f.source_url:
                continue
            key = f.source_url or f.source_name or ""
            if key in seen_urls:
                continue
            seen_urls.add(key)
            sources.append(
                {
                    "name": f.source_name or "Unknown",
                    "url": f.source_url,
                    "type": f.source_type or "unknown",
                    "accessed_at": f.created_at.isoformat() if f.created_at else None,
                }
            )
        return sources

    # ------------------------------------------------------------------
    # Section generation
    # ------------------------------------------------------------------

    def _generate_section(
        self,
        title: str,
        purpose: str,
        findings: list[Finding],
        structured_data: dict,
        mission_context: dict,
        confidence_filter: float | None = None,
    ) -> dict:
        """Generate one report section using Gemini.

        Returns a dict with keys: title, content_md, finding_ids_used,
        chart_configs, order.
        """
        # Apply confidence filter when specified
        relevant = (
            [f for f in findings if f.confidence >= confidence_filter]
            if confidence_filter is not None
            else list(findings)
        )

        finding_ids_used = [str(f.id) for f in relevant]
        findings_text = self._format_findings_for_prompt(relevant) if relevant else "No findings available for this section."

        structured_snippet = ""
        if structured_data:
            try:
                structured_snippet = json.dumps(structured_data, indent=2, default=str)[:4000]
            except (TypeError, ValueError):
                structured_snippet = str(structured_data)[:4000]

        prompt = (
            f"You are writing a section of a professional research report.\n\n"
            f"## Mission Context\n"
            f"Title: {mission_context.get('title', 'N/A')}\n"
            f"Objective: {mission_context.get('objective', 'N/A')}\n"
            f"Description: {mission_context.get('description', 'N/A')}\n\n"
            f"## Section: {title}\n"
            f"Purpose: {purpose}\n\n"
            f"## Research Findings\n"
            f"{findings_text}\n\n"
        )
        if structured_snippet:
            prompt += f"## Structured Data\n```json\n{structured_snippet}\n```\n\n"

        prompt += (
            "## Instructions\n"
            "- Write the section content in polished Markdown.\n"
            "- Do NOT include the section title as a heading (it will be added automatically).\n"
            "- Cite sources inline using the source name and URL where available.\n"
            "- Note confidence levels when presenting findings (e.g., 'with high confidence' for >= 0.8).\n"
            "- Flag limitations or low-confidence data explicitly.\n"
            "- Use tables, bullet points, and sub-headings as appropriate.\n"
            "- Be concise but thorough. Avoid filler.\n"
            "- If there are no relevant findings, state that clearly rather than fabricating content.\n"
        )

        try:
            content_md = self._call_gemini(prompt)
        except Exception as exc:
            logger.error("Gemini call failed for section '%s': %s", title, exc)
            content_md = (
                f"*Section generation failed due to an API error. "
                f"{len(relevant)} finding(s) were available for this section.*"
            )

        # Attempt to extract chart configs from structured data
        chart_configs: list[dict] = []
        if structured_data and relevant:
            try:
                chart_configs = self.chart_gen.suggest_charts(
                    section_title=title,
                    structured_data=structured_data,
                    findings=relevant,
                )
            except Exception as exc:
                logger.warning("Chart suggestion failed for section '%s': %s", title, exc)

        return {
            "title": title,
            "content_md": content_md,
            "finding_ids_used": finding_ids_used,
            "chart_configs": chart_configs,
            "order": 0,  # caller sets actual order
        }

    # ------------------------------------------------------------------
    # Executive summary
    # ------------------------------------------------------------------

    def _generate_executive_summary(self, sections: list[dict], mission: Mission) -> str:
        """Generate a concise executive summary from completed sections."""
        section_summaries = "\n\n".join(
            f"### {s['title']}\n{s['content_md'][:800]}"
            for s in sections
            if s.get("content_md")
        )

        prompt = (
            f"You are writing the Executive Summary for a research report.\n\n"
            f"## Mission\n"
            f"Title: {mission.title}\n"
            f"Objective: {mission.objective or 'N/A'}\n"
            f"Description: {mission.description or 'N/A'}\n"
            f"Overall Confidence: {mission.confidence_score or 'N/A'}\n"
            f"Total Findings: {mission.findings_count}\n\n"
            f"## Section Summaries\n{section_summaries}\n\n"
            f"## Instructions\n"
            f"- Write a concise executive summary (3-5 paragraphs maximum).\n"
            f"- Highlight the most important discoveries and their implications.\n"
            f"- Include recommended next steps.\n"
            f"- Use a professional, scannable style.\n"
            f"- Do NOT include a heading. The heading is added automatically.\n"
        )

        try:
            return self._call_gemini(prompt)
        except Exception as exc:
            logger.error("Failed to generate executive summary: %s", exc)
            return "*Executive summary generation failed due to an API error.*"

    # ------------------------------------------------------------------
    # Methodology
    # ------------------------------------------------------------------

    def _generate_methodology(self, crew_runs: list[CrewRun], mission: Mission) -> str:
        """Describe how the research was conducted."""
        runs_text = "No crew run data available."
        if crew_runs:
            parts: list[str] = []
            for run in crew_runs:
                duration = (
                    f"{run.duration_seconds:.0f}s" if run.duration_seconds else "N/A"
                )
                metrics_str = json.dumps(run.metrics, default=str) if run.metrics else "{}"
                parts.append(
                    f"- Run {run.iteration} | Status: {run.status} | "
                    f"Duration: {duration} | Metrics: {metrics_str}"
                )
                if run.summary:
                    parts.append(f"  Summary: {run.summary}")
            runs_text = "\n".join(parts)

        scope_text = json.dumps(mission.scope, default=str) if mission.scope else "N/A"

        prompt = (
            f"You are writing the Methodology section for a research report.\n\n"
            f"## Mission\n"
            f"Title: {mission.title}\n"
            f"Objective: {mission.objective or 'N/A'}\n"
            f"Scope: {scope_text}\n"
            f"Started: {mission.started_at or 'N/A'}\n"
            f"Completed: {mission.completed_at or 'N/A'}\n"
            f"Total Duration: {mission.duration_seconds or 'N/A'} seconds\n\n"
            f"## Crew Runs (research execution details)\n{runs_text}\n\n"
            f"## Instructions\n"
            f"- Describe the research approach, expert agents used, and sources queried.\n"
            f"- Include timing and scope information.\n"
            f"- Be factual and specific about what was done.\n"
            f"- Do NOT include a heading. The heading is added automatically.\n"
        )

        try:
            return self._call_gemini(prompt)
        except Exception as exc:
            logger.error("Failed to generate methodology: %s", exc)
            return "*Methodology section generation failed due to an API error.*"

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def generate_report(
        self,
        mission_id: uuid.UUID,
        report_type: str,
        config: dict | None,
        db: Session,
    ) -> Report:
        """Full report generation pipeline.

        Steps:
          1. Load mission and validate it exists
          2. Load all findings sorted by category + confidence
          3. Load crew runs for methodology
          4. Get report template
          5. For each template section: generate narrative via Gemini
          6. Generate charts from numerical/structured data
          7. Write executive summary (after all sections done)
          8. Write methodology section
          9. Compile source list with access dates
         10. Render Markdown -> HTML using markdown2
         11. Create and save Report record
        """
        start_time = time.monotonic()

        # ---- 1. Load mission ----
        mission = db.query(Mission).filter(Mission.id == mission_id).first()
        if mission is None:
            raise ValueError(f"Mission {mission_id} not found")

        mission_context = {
            "title": mission.title,
            "description": mission.description,
            "objective": mission.objective,
            "scope": mission.scope,
            "status": mission.status,
            "confidence_score": mission.confidence_score,
        }

        # ---- 2. Load findings ----
        findings: list[Finding] = (
            db.query(Finding)
            .filter(Finding.mission_id == mission_id)
            .order_by(Finding.category, Finding.confidence.desc())
            .all()
        )
        logger.info(
            "Loaded %d findings for mission %s", len(findings), mission_id
        )

        # ---- 3. Load crew runs ----
        crew_runs: list[CrewRun] = (
            db.query(CrewRun)
            .filter(CrewRun.mission_id == mission_id)
            .order_by(CrewRun.started_at)
            .all()
        )

        # ---- 4. Load template ----
        template = self._load_template(report_type)
        template_sections = template.get("sections", [])

        # ---- 5. Aggregate structured data ----
        aggregated_structured = self._aggregate_structured_data(findings)

        # ---- 6. Generate each section ----
        generated_sections: list[dict] = []
        all_charts: list[dict] = []
        executive_summary_text = ""
        methodology_text = ""

        for section_def in template_sections:
            section_title = section_def["title"]
            section_purpose = section_def["purpose"]
            section_order = section_def.get("order", 0)
            confidence_filter = section_def.get("confidence_filter")

            # Skip auto-generated special sections; we handle them after
            if section_title == "Executive Summary":
                continue
            if section_title in ("Methodology", "Methodology & Sources"):
                continue

            logger.info("Generating section: %s", section_title)
            section = self._generate_section(
                title=section_title,
                purpose=section_purpose,
                findings=findings,
                structured_data=aggregated_structured,
                mission_context=mission_context,
                confidence_filter=confidence_filter,
            )
            section["order"] = section_order
            generated_sections.append(section)

            if section.get("chart_configs"):
                all_charts.extend(section["chart_configs"])

        # ---- 7. Executive summary ----
        logger.info("Generating executive summary")
        executive_summary_text = self._generate_executive_summary(
            generated_sections, mission
        )

        # ---- 8. Methodology ----
        logger.info("Generating methodology section")
        methodology_text = self._generate_methodology(crew_runs, mission)

        # ---- 9. Compile sources ----
        sources = self._compile_sources(findings)

        # ---- 10. Assemble full Markdown ----
        md_parts: list[str] = [f"# {mission.title}\n"]

        # Executive summary first
        md_parts.append(f"## Executive Summary\n\n{executive_summary_text}\n")

        # Body sections in order
        sorted_sections = sorted(generated_sections, key=lambda s: s["order"])
        for sec in sorted_sections:
            md_parts.append(f"## {sec['title']}\n\n{sec['content_md']}\n")

        # Methodology
        md_parts.append(f"## Methodology\n\n{methodology_text}\n")

        # Sources
        if sources:
            md_parts.append("## Sources & References\n")
            for src in sources:
                url_part = f" - [{src['url']}]({src['url']})" if src.get("url") else ""
                accessed = f" (accessed {src['accessed_at'][:10]})" if src.get("accessed_at") else ""
                md_parts.append(f"- **{src['name']}**{url_part}{accessed}")
            md_parts.append("")

        content_markdown = "\n\n".join(md_parts)

        # ---- 10b. Render HTML ----
        content_html = markdown2.markdown(content_markdown, extras=MARKDOWN2_EXTRAS)

        # ---- 11. Build sections JSON for storage ----
        exec_section = {
            "title": "Executive Summary",
            "content_md": executive_summary_text,
            "finding_ids_used": [],
            "chart_configs": [],
            "order": 0,
        }
        methodology_section = {
            "title": "Methodology",
            "content_md": methodology_text,
            "finding_ids_used": [],
            "chart_configs": [],
            "order": max((s["order"] for s in sorted_sections), default=0) + 1,
        }
        all_sections_json = [exec_section] + sorted_sections + [methodology_section]

        # ---- 12. Calculate metadata ----
        generation_time = time.monotonic() - start_time
        word_count = len(content_markdown.split())
        confidence_values = [f.confidence for f in findings if f.confidence is not None]
        confidence_avg = (
            sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        )

        metadata = {
            "total_findings": len(findings),
            "total_sources": len(sources),
            "confidence_avg": round(confidence_avg, 3),
            "generation_time_seconds": round(generation_time, 2),
            "word_count": word_count,
            "template_used": report_type,
            "model": _REPORT_MODEL,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # ---- 13. Create Report record ----
        report = Report(
            id=uuid.uuid4(),
            title=f"{template.get('name', 'Report')}: {mission.title}",
            description=mission.description,
            report_type=report_type,
            status="ready",
            content_markdown=content_markdown,
            content_html=content_html,
            sections=all_sections_json,
            executive_summary=executive_summary_text,
            methodology=methodology_text,
            sources=sources,
            charts=all_charts if all_charts else None,
            structured_data=aggregated_structured if aggregated_structured else None,
            metadata_=metadata,
            project_id=mission.project_id,
            mission_id=mission.id,
            user_id=mission.user_id,
        )

        try:
            # Track lifecycle: generating -> ready
            _append_report_transition(report, "generating", "ready", "Report generation completed")
            db.add(report)
            db.commit()
            db.refresh(report)
            logger.info(
                "Report %s created successfully in %.1fs (%d words)",
                report.id,
                generation_time,
                word_count,
            )
        except Exception as exc:
            db.rollback()
            report.failure_category = FailureCategory.internal
            report.failure_message = str(exc)
            _append_report_transition(report, "generating", "failed", str(exc))
            logger.error("Failed to save report: %s", exc)
            raise

        return report

    # ------------------------------------------------------------------
    # Section regeneration
    # ------------------------------------------------------------------

    def regenerate_section(
        self,
        report_id: uuid.UUID,
        section_index: int,
        instructions: str | None,
        db: Session,
    ) -> Report:
        """Regenerate a single section of an existing report.

        Optionally accepts user instructions to guide the regeneration.
        """
        report = db.query(Report).filter(Report.id == report_id).first()
        if report is None:
            raise ValueError(f"Report {report_id} not found")

        sections: list[dict] = list(report.sections or [])
        if section_index < 0 or section_index >= len(sections):
            raise IndexError(
                f"Section index {section_index} out of range (0-{len(sections) - 1})"
            )

        target_section = dict(sections[section_index])
        section_title = target_section["title"]
        logger.info(
            "Regenerating section '%s' (index %d) of report %s",
            section_title,
            section_index,
            report_id,
        )

        # Load mission and findings for context
        mission = db.query(Mission).filter(Mission.id == report.mission_id).first()
        if mission is None:
            raise ValueError(f"Mission {report.mission_id} not found for report")

        findings: list[Finding] = (
            db.query(Finding)
            .filter(Finding.mission_id == report.mission_id)
            .order_by(Finding.category, Finding.confidence.desc())
            .all()
        )

        mission_context = {
            "title": mission.title,
            "description": mission.description,
            "objective": mission.objective,
            "scope": mission.scope,
            "status": mission.status,
            "confidence_score": mission.confidence_score,
        }

        aggregated_structured = self._aggregate_structured_data(findings)

        # Load template to get the section purpose
        template = self._load_template(report.report_type or "research_report")
        purpose = "Provide a thorough analysis based on the available findings."
        confidence_filter: float | None = None
        for tpl_section in template.get("sections", []):
            if tpl_section["title"] == section_title:
                purpose = tpl_section["purpose"]
                confidence_filter = tpl_section.get("confidence_filter")
                break

        # Handle special sections
        if section_title == "Executive Summary":
            other_sections = [s for s in sections if s["title"] != "Executive Summary"]
            new_content = self._generate_executive_summary(other_sections, mission)
            target_section["content_md"] = new_content
        elif section_title in ("Methodology", "Methodology & Sources"):
            crew_runs = (
                db.query(CrewRun)
                .filter(CrewRun.mission_id == report.mission_id)
                .order_by(CrewRun.started_at)
                .all()
            )
            new_content = self._generate_methodology(crew_runs, mission)
            target_section["content_md"] = new_content
        else:
            # Augment purpose with user instructions if provided
            augmented_purpose = purpose
            if instructions:
                augmented_purpose = (
                    f"{purpose}\n\nAdditional instructions from the user:\n{instructions}"
                )

            new_section = self._generate_section(
                title=section_title,
                purpose=augmented_purpose,
                findings=findings,
                structured_data=aggregated_structured,
                mission_context=mission_context,
                confidence_filter=confidence_filter,
            )
            target_section["content_md"] = new_section["content_md"]
            target_section["finding_ids_used"] = new_section["finding_ids_used"]
            target_section["chart_configs"] = new_section["chart_configs"]

        # Update the sections list immutably
        updated_sections = [
            target_section if i == section_index else dict(s)
            for i, s in enumerate(sections)
        ]

        # Rebuild full markdown
        md_parts: list[str] = [f"# {mission.title}\n"]
        for sec in sorted(updated_sections, key=lambda s: s.get("order", 0)):
            md_parts.append(f"## {sec['title']}\n\n{sec['content_md']}\n")
        content_markdown = "\n\n".join(md_parts)
        content_html = markdown2.markdown(content_markdown, extras=MARKDOWN2_EXTRAS)

        # Recalculate metadata
        existing_metadata = dict(report.metadata_ or {})
        existing_metadata["word_count"] = len(content_markdown.split())
        existing_metadata["last_section_regenerated"] = section_title
        existing_metadata["last_regenerated_at"] = datetime.now(timezone.utc).isoformat()

        # Collect all charts from updated sections
        all_charts = []
        for sec in updated_sections:
            all_charts.extend(sec.get("chart_configs", []))

        # Update report fields
        report.sections = updated_sections
        report.content_markdown = content_markdown
        report.content_html = content_html
        report.metadata_ = existing_metadata
        report.charts = all_charts if all_charts else None

        # Update executive summary / methodology text if those were regenerated
        if section_title == "Executive Summary":
            report.executive_summary = target_section["content_md"]
        elif section_title in ("Methodology", "Methodology & Sources"):
            report.methodology = target_section["content_md"]

        try:
            db.commit()
            db.refresh(report)
            logger.info("Section '%s' regenerated for report %s", section_title, report_id)
        except Exception as exc:
            db.rollback()
            logger.error("Failed to save regenerated section: %s", exc)
            raise

        return report
