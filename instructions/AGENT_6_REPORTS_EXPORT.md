# AGENT 6 — Reports, Charts & Data Export

## YOUR MISSION

You are a Claude Code agent. Build the **output layer** — everything that turns raw research findings into polished, usable deliverables: narrative reports, charts, PDFs, data exports, interactive tables, and shareable links.

**Start:** `/plan Read this entire file, explore the repo, then build everything.`

---

## WHAT YOU'RE BUILDING

When missions complete, users need:
1. **Rich narrative reports** — Markdown/HTML/PDF with sections, executive summary, citations, confidence badges
2. **Auto-generated charts** — bar, line, pie, scatter from structured data
3. **Structured data export** — CSV, JSON, Excel
4. **Interactive data explorer** — filterable/sortable tables in the dashboard
5. **Shareable links** — send a report to someone without an account

---

## MODELS

### report.py
Fields: id (UUID PK), project_id (FK projects), mission_id (FK missions nullable), user_id (FK users), title (str 500), description (Text nullable), report_type (str: research_report|market_analysis|competitive_intel|due_diligence|property_report|custom), status (str: generating|ready|failed), content_markdown (Text — full report in Markdown), content_html (Text nullable — rendered HTML), sections (JSONB — [{title, content_md, finding_ids, chart_configs, order}]), executive_summary (Text), methodology (Text), sources (JSONB — [{name, url, type, access_date}]), charts (JSONB — [{id, type, title, data, options}] — Chart.js configs), structured_data (JSONB — all machine-readable data), metadata (JSONB: {total_findings, total_sources, confidence_avg, generation_time_seconds, word_count}), format_config (JSONB: {theme, logo_url, cover_page, toc, page_numbers}), share_token (str nullable unique), share_enabled (Bool default false), pdf_url (Text nullable), created_at, updated_at.

---

## SERVICES

### report_generator.py — MAIN REPORT ENGINE

```python
class ReportGenerator:
    """Generates polished research reports from mission findings using Gemini."""

    async def generate_report(self, mission_id: UUID, report_type: str = "research_report",
                               config: dict = None, db=None) -> Report:
        """
        Full pipeline:
        1. Load all findings sorted by category + confidence
        2. Load research results and structured data
        3. Get report template (section structure) for report_type
        4. Use Gemini to plan section ordering and content allocation
        5. For each section: generate narrative from relevant findings via Gemini
        6. Generate charts from numerical data
        7. Write executive summary (after all sections done)
        8. Write methodology section
        9. Compile source list with access dates
        10. Render Markdown → HTML
        11. Save report
        """

    async def _generate_section(self, title: str, purpose: str, findings: list,
                                 structured_data: dict, mission_context: dict) -> dict:
        """
        Generate one section using Gemini.
        Prompt includes: section purpose, relevant findings with confidence,
        structured data, instructions to cite sources + note confidence + flag limitations.
        Returns: {title, content_md, finding_ids_used, charts_generated}
        """

    async def _generate_executive_summary(self, sections: list, mission: Mission) -> str:
        """Concise summary from completed sections. 3-5 paragraphs max."""

    async def _generate_methodology(self, crew_run, mission) -> str:
        """Describe how research was conducted: experts used, sources queried, confidence approach."""

    async def regenerate_section(self, report_id: UUID, section_index: int,
                                  instructions: str = None, db=None) -> Report:
        """Regenerate a single section with optional user instructions."""
```

### chart_generator.py

```python
class ChartGenerator:
    """Generates Chart.js configuration objects from data."""

    async def auto_generate_charts(self, structured_data: dict, context: str) -> list[dict]:
        """
        Use Gemini to analyze structured data and decide what deserves visualization.
        Returns list of Chart.js configs ready for frontend rendering.

        For each chart:
        {
            "id": "price_comparison",
            "type": "bar",  # bar|line|pie|doughnut|scatter|radar
            "title": "Gas Prices by Station",
            "data": {
                "labels": ["Shell", "Chevron", "Exxon", "BP"],
                "datasets": [{
                    "label": "Regular ($/gal)",
                    "data": [3.29, 3.35, 3.19, 3.45],
                    "backgroundColor": ["#4F46E5", "#7C3AED", "#2563EB", "#0891B2"]
                }]
            },
            "options": {
                "responsive": true,
                "plugins": {"title": {"display": true, "text": "Gas Prices by Station"}}
            }
        }
        """

    def comparison_bar_chart(self, items: list[dict], value_field: str,
                              label_field: str, title: str) -> dict:
        """Create a bar chart comparing items on a metric."""

    def trend_line_chart(self, timeseries: list[dict], date_field: str,
                          value_field: str, title: str) -> dict:
        """Create a line chart showing trend over time."""

    def distribution_histogram(self, values: list[float], title: str, bins: int = 10) -> dict:
        """Create a histogram showing value distribution."""

    def pie_chart(self, categories: dict[str, float], title: str) -> dict:
        """Create a pie chart from category → value mapping."""

    def scatter_plot(self, points: list[dict], x_field: str, y_field: str,
                      label_field: str, title: str) -> dict:
        """Create scatter plot (e.g., price vs sqft for properties)."""

    def multi_series_line(self, series: dict[str, list[dict]], date_field: str,
                           value_field: str, title: str) -> dict:
        """Multiple lines on one chart (e.g., price trends for different areas)."""

    def generate_map_pins(self, locations: list[dict]) -> dict:
        """Generate data for a map visualization (lat/lng pins with labels)."""
```

### pdf_exporter.py

```python
class PDFExporter:
    """Export reports to professional PDFs."""

    async def export_to_pdf(self, report: Report) -> bytes:
        """
        Pipeline: Markdown → HTML (with CSS) → PDF (via WeasyPrint)

        PDF features:
        - Cover page: title, date, project name, Agentary branding
        - Table of contents (auto-generated from headings)
        - Professional typography (system fonts, proper spacing)
        - Headers: report title. Footers: page numbers
        - Charts rendered as embedded SVG or PNG (use matplotlib to render Chart.js configs)
        - Source citations as footnotes or endnotes
        - Confidence badges: 🟢 High (>0.8), 🟡 Medium (0.5-0.8), 🔴 Low (<0.5) — as colored dots
        - Clean table styling for structured data
        - Page breaks between major sections
        """

    async def _render_charts_as_images(self, charts: list[dict]) -> dict[str, bytes]:
        """Render Chart.js configs to PNG images using matplotlib recreation."""

    async def _build_html(self, report: Report, chart_images: dict) -> str:
        """Build complete HTML document with embedded CSS and chart images."""

    async def export_to_html(self, report: Report) -> str:
        """Standalone HTML page with embedded CSS, Chart.js, interactive charts."""

    async def export_to_markdown(self, report: Report) -> str:
        """Clean Markdown export (charts become tables or image refs)."""
```

### data_exporter.py

```python
class DataExporter:
    """Export structured research data in various formats."""

    async def export_findings_csv(self, mission_id: UUID, filters: dict = None, db=None) -> bytes:
        """
        CSV with columns: title, category, content, confidence, source_type,
        source_name, source_url, expert, tags, created_at.
        Apply optional filters: category, confidence_min, expert_slug, source_type.
        """

    async def export_findings_json(self, mission_id: UUID, filters: dict = None, db=None) -> str:
        """JSON array of finding objects with all fields."""

    async def export_findings_excel(self, mission_id: UUID, filters: dict = None, db=None) -> bytes:
        """
        Excel workbook (openpyxl) with multiple sheets:
        - Summary (mission info, stats)
        - All Findings (main data)
        - By Category (one sheet per category)
        - Structured Data (if available)
        - Sources (deduplicated source list)
        Proper column widths, header styling, filters enabled.
        """

    async def export_structured_data(self, mission_id: UUID, format: str, db=None) -> bytes:
        """Export the mission's structured_data in CSV, JSON, or Excel."""

    async def export_entity_collection_csv(self, collection_id: UUID, db=None) -> bytes:
        """Export entity collection as CSV with canonical_data fields as columns."""
```

### share_service.py

```python
class ShareService:
    """Manage shareable report links."""

    async def create_share_link(self, report_id: UUID, user_id: UUID, db) -> str:
        """Generate unique share token, enable sharing, return full URL."""
        token = secrets.token_urlsafe(32)
        report.share_token = token
        report.share_enabled = True
        return f"{settings.BASE_URL}/shared/reports/{token}"

    async def get_shared_report(self, share_token: str, db) -> Report | None:
        """Fetch report by token. No auth required. Returns None if not found or disabled."""

    async def revoke_share(self, report_id: UUID, user_id: UUID, db):
        """Disable sharing, clear token."""
```

---

## REPORT TEMPLATES

Define section structures for each report type:

### 1. Research Report (generic)
Sections: Executive Summary, Background & Context, Methodology, Key Findings (filter confidence >= 0.7), Detailed Analysis (with charts), Supporting Data, Limitations & Caveats, Sources & References.

### 2. Market Analysis
Sections: Executive Summary, Market Overview (with size/growth charts), Competitive Landscape, Pricing Analysis (comparison charts), Trends & Projections (trend charts), Opportunities & Risks, Recommendations, Methodology & Sources.

### 3. Property Report
Sections: Property Overview, Market Context (area stats + charts), Comparable Sales Analysis (comp table + charts), Price Analysis (price/sqft trends), Neighborhood Profile (schools, crime, amenities), Permit & Construction Activity, Investment Analysis (ROI projections), Sources.

### 4. Competitive Intelligence
Sections: Executive Summary, Company Profiles, Feature Comparison (matrix table), Pricing Comparison (chart), Market Positioning, Strengths & Weaknesses (per competitor), Strategic Recommendations, Sources.

### 5. Due Diligence
Sections: Executive Summary, Company Overview, Financial Health, Leadership & Team, Legal & Compliance, Market Position, Technology & IP, Risks & Red Flags, Recommendation, Sources.

Store templates as JSON in `backend/app/services/reports/templates/`.

---

## API ROUTES

### `/api/reports`
- POST / — generate report {mission_id, report_type, config?}. Returns report_id, status=generating. Celery task does the work.
- GET / — list reports for user/project
- GET /{id} — full report with content, sections, charts
- PUT /{id} — update (edit title, description)
- DELETE /{id}
- POST /{id}/regenerate — regenerate entire report
- POST /{id}/regenerate-section — regenerate one section {section_index, instructions?}
- GET /{id}/pdf — download PDF (generate on-the-fly or return cached)
- GET /{id}/html — get standalone HTML
- GET /{id}/markdown — get Markdown
- POST /{id}/share — create share link → returns {url, token}
- DELETE /{id}/share — revoke

### `/api/shared/reports/{token}` (NO AUTH REQUIRED)
- GET / — view shared report (public page)

### `/api/export`
- GET /missions/{id}/findings/csv?category=...&confidence_min=...
- GET /missions/{id}/findings/json
- GET /missions/{id}/findings/excel
- GET /missions/{id}/structured-data/{format}
- GET /entity-collections/{id}/csv

---

## CELERY TASKS

```python
@celery_app.task(name="report.generate", queue="reports", soft_time_limit=300, time_limit=360)
def generate_report_task(report_id: str):
    """Generate report in background. Updates status: generating → ready|failed."""

@celery_app.task(name="report.generate_pdf", queue="reports")
def generate_pdf_task(report_id: str):
    """Generate PDF, store, update pdf_url field."""
```

---

## FRONTEND PAGES

### Report Viewer (`/reports/[id]`)
- **Clean, readable layout** — left sidebar with TOC (clickable section links), main content area
- **Sections** rendered from Markdown → HTML with proper typography
- **Charts** rendered inline using Chart.js (React: react-chartjs-2) or Recharts
- **Confidence badges** on key claims: colored dots 🟢🟡🔴 with tooltip showing score
- **Source links** — numbered citations, clickable
- **Structured data tables** — inline where referenced in report
- **Toolbar:** Download PDF, Download Markdown, Download Data (CSV/Excel), Share, Print, Regenerate
- **Edit mode:** click section header → "Regenerate this section" with optional instructions input

### Data Explorer (tab on Mission Detail page)
- Interactive table of all findings and structured data
- Column sorting, filtering, full-text search
- Group by: category, expert, source type
- Confidence filter slider
- Export buttons (CSV, JSON, Excel)
- Click row → expand to see full content + source

### Report Generation UI (shown after mission completes)
```
┌──────────────────────────────────────────────┐
│  ✅ Mission Complete! 47 findings, 12 sources │
│                                               │
│  Generate Report:                             │
│  ● Research Report                            │
│  ○ Market Analysis                            │
│  ○ Property Report                            │
│  ○ Competitive Intel                          │
│  ○ Due Diligence                              │
│                                               │
│  ☑ Include charts  ☑ Data tables  ☑ Sources   │
│                                               │
│                         [Generate Report →]    │
└──────────────────────────────────────────────┘
```

### Shared Report Page (`/shared/reports/[token]`)
- Public page (no login)
- Read-only report viewer with Agentary branding
- "Powered by Agentary" footer with signup link
- No edit/regenerate/export capabilities

---

## DEPENDENCIES

Install these in the backend:
```
weasyprint        # HTML → PDF rendering
openpyxl          # Excel (.xlsx) generation
markdown2         # Markdown → HTML conversion
pygments          # Code syntax highlighting
matplotlib        # Chart rendering for PDFs (recreate Chart.js as matplotlib figures)
beautifulsoup4    # HTML manipulation (should already exist)
```

Frontend:
```
react-chartjs-2   # Chart.js React wrapper
chart.js           # Chart rendering
react-markdown     # Markdown rendering in React
```

---

## SUCCESS CRITERIA (Agent 7 Checks)

- [ ] Report model with migration
- [ ] ReportGenerator produces multi-section reports from findings via Gemini
- [ ] 5 report templates (research, market, property, competitive, due diligence)
- [ ] Section regeneration with user instructions
- [ ] ChartGenerator creates 6+ chart types (bar, line, pie, scatter, histogram, multi-line)
- [ ] Auto-chart generation (Gemini decides what to visualize)
- [ ] PDFExporter generates professional PDFs with cover, TOC, charts, citations
- [ ] HTML and Markdown export
- [ ] DataExporter: CSV, JSON, Excel (multi-sheet) for findings
- [ ] Excel export has proper formatting (column widths, headers, filters)
- [ ] ShareService: create/revoke share links
- [ ] Public shared report page (no auth)
- [ ] API routes for reports, export, sharing
- [ ] Frontend: report viewer with TOC, inline charts, confidence badges
- [ ] Frontend: data explorer with sortable/filterable table
- [ ] Frontend: report generation UI
- [ ] Celery tasks for background generation
- [ ] docs/PHASE_6_PROGRESS.md updated
