import base64
import io
import logging
from datetime import datetime

import markdown2
import matplotlib

matplotlib.use("Agg")  # Non-interactive backend — must be set before pyplot import
import matplotlib.pyplot as plt
import numpy as np

from ...models.report import Report

logger = logging.getLogger(__name__)


class PDFExporter:
    """Export reports to professional PDFs, standalone HTML, and Markdown."""

    # ------------------------------------------------------------------ #
    #  Professional CSS for PDF rendering                                 #
    # ------------------------------------------------------------------ #
    PDF_CSS = """
    /* ── Page rules ─────────────────────────────────────────────────── */
    @page {
        size: A4;
        margin: 25mm 20mm 30mm 20mm;

        @top-center {
            content: string(report-title);
            font-family: Helvetica, Arial, sans-serif;
            font-size: 8pt;
            color: #888;
            border-bottom: 0.5pt solid #ccc;
            padding-bottom: 4pt;
        }

        @bottom-center {
            content: "Page " counter(page) " of " counter(pages);
            font-family: Helvetica, Arial, sans-serif;
            font-size: 8pt;
            color: #888;
        }
    }

    @page :first {
        @top-center { content: none; }
        @bottom-center { content: none; }
    }

    /* ── Base typography ────────────────────────────────────────────── */
    body {
        font-family: Helvetica, Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #222;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }

    h1 { font-size: 22pt; color: #1a1a2e; margin-top: 0; margin-bottom: 8pt; }
    h2 { font-size: 17pt; color: #16213e; margin-top: 20pt; margin-bottom: 6pt; border-bottom: 1.5pt solid #e0e0e0; padding-bottom: 4pt; }
    h3 { font-size: 14pt; color: #1a1a2e; margin-top: 14pt; margin-bottom: 4pt; }
    h4 { font-size: 12pt; color: #333; margin-top: 10pt; margin-bottom: 4pt; }

    p { margin: 6pt 0; }

    a { color: #2563eb; text-decoration: none; }

    /* ── Cover page ─────────────────────────────────────────────────── */
    .cover-page {
        page-break-after: always;
        text-align: center;
        padding-top: 120pt;
    }
    .cover-page .brand {
        font-size: 12pt;
        text-transform: uppercase;
        letter-spacing: 4pt;
        color: #6c63ff;
        margin-bottom: 40pt;
    }
    .cover-page .title {
        font-size: 32pt;
        font-weight: bold;
        color: #1a1a2e;
        margin-bottom: 16pt;
        line-height: 1.2;
        string-set: report-title content();
    }
    .cover-page .subtitle {
        font-size: 14pt;
        color: #555;
        margin-bottom: 40pt;
    }
    .cover-page .meta {
        font-size: 10pt;
        color: #777;
        margin-top: 60pt;
    }
    .cover-page .meta .date { margin-bottom: 4pt; }
    .cover-page .meta .report-type {
        text-transform: capitalize;
        background: #f0f0ff;
        display: inline-block;
        padding: 4pt 12pt;
        border-radius: 4pt;
        color: #6c63ff;
        font-weight: 600;
    }

    /* ── Table of contents ──────────────────────────────────────────── */
    .toc {
        page-break-after: always;
    }
    .toc h2 {
        border-bottom: none;
        text-align: center;
    }
    .toc ul {
        list-style: none;
        padding: 0;
        margin: 16pt 0;
    }
    .toc li {
        padding: 6pt 0;
        border-bottom: 1pt dotted #ccc;
        font-size: 11pt;
    }
    .toc li .toc-number {
        display: inline-block;
        width: 24pt;
        color: #6c63ff;
        font-weight: 600;
    }

    /* ── Sections ───────────────────────────────────────────────────── */
    .section {
        page-break-before: always;
    }
    .section:first-of-type {
        page-break-before: avoid;
    }
    .executive-summary {
        background: #f8f9ff;
        border-left: 4pt solid #6c63ff;
        padding: 12pt 16pt;
        margin: 16pt 0;
        border-radius: 0 4pt 4pt 0;
    }

    /* ── Tables ─────────────────────────────────────────────────────── */
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 12pt 0;
        font-size: 10pt;
    }
    thead th {
        background: #1a1a2e;
        color: #fff;
        padding: 8pt 10pt;
        text-align: left;
        font-weight: 600;
    }
    tbody td {
        padding: 6pt 10pt;
        border-bottom: 0.5pt solid #e0e0e0;
    }
    tbody tr:nth-child(even) {
        background: #f9f9fb;
    }

    /* ── Chart images ───────────────────────────────────────────────── */
    .chart-container {
        text-align: center;
        margin: 16pt 0;
        page-break-inside: avoid;
    }
    .chart-container img {
        max-width: 100%;
        height: auto;
    }
    .chart-container .chart-title {
        font-size: 11pt;
        font-weight: 600;
        color: #333;
        margin-bottom: 8pt;
    }

    /* ── Confidence badges ──────────────────────────────────────────── */
    .badge {
        display: inline-block;
        width: 10pt;
        height: 10pt;
        border-radius: 50%;
        margin-right: 4pt;
        vertical-align: middle;
    }
    .badge-high   { background: #22c55e; }
    .badge-medium { background: #eab308; }
    .badge-low    { background: #ef4444; }
    .confidence-label {
        font-size: 9pt;
        color: #666;
        vertical-align: middle;
    }

    /* ── Blockquotes / citations ────────────────────────────────────── */
    blockquote {
        border-left: 3pt solid #d1d5db;
        margin: 10pt 0;
        padding: 6pt 14pt;
        color: #555;
        font-style: italic;
        background: #fafafa;
    }

    /* ── Source list ─────────────────────────────────────────────────── */
    .sources {
        page-break-before: always;
    }
    .sources ol {
        padding-left: 20pt;
    }
    .sources li {
        margin-bottom: 6pt;
        font-size: 10pt;
        line-height: 1.5;
    }
    .sources .source-type {
        display: inline-block;
        font-size: 8pt;
        background: #e0e7ff;
        color: #3730a3;
        padding: 1pt 6pt;
        border-radius: 3pt;
        margin-left: 4pt;
        text-transform: uppercase;
    }
    .sources .access-date {
        font-size: 8pt;
        color: #999;
        margin-left: 4pt;
    }

    /* ── Code blocks ────────────────────────────────────────────────── */
    pre {
        background: #f4f4f8;
        padding: 10pt 14pt;
        border-radius: 4pt;
        font-size: 9pt;
        line-height: 1.5;
        overflow-x: auto;
        border: 0.5pt solid #e0e0e0;
    }
    code {
        font-family: "Courier New", Courier, monospace;
        font-size: 9pt;
    }

    /* ── Misc ───────────────────────────────────────────────────────── */
    hr {
        border: none;
        border-top: 1pt solid #e0e0e0;
        margin: 16pt 0;
    }
    ul, ol { margin: 6pt 0; padding-left: 20pt; }
    li { margin-bottom: 3pt; }
    """

    # Colors used for matplotlib chart rendering
    _CHART_COLORS = [
        "#6c63ff", "#ff6584", "#43aa8b", "#f9c74f",
        "#90be6d", "#577590", "#f3722c", "#4cc9f0",
        "#7209b7", "#3a0ca3",
    ]

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def export_to_pdf(self, report: Report) -> bytes:
        """Build HTML then convert to PDF bytes via WeasyPrint.

        Raises ``RuntimeError`` if WeasyPrint is not installed.
        """
        try:
            from weasyprint import HTML as WeasyprintHTML
        except ImportError as exc:
            raise RuntimeError(
                "WeasyPrint is required for PDF export but is not installed. "
                "Install it with: pip install weasyprint"
            ) from exc

        chart_images = self._render_charts_as_images(report.charts)
        full_html = self._build_html(report, chart_images)

        html_obj = WeasyprintHTML(string=full_html)
        return html_obj.write_pdf()

    def export_to_html(self, report: Report) -> str:
        """Return a self-contained HTML page with interactive Chart.js charts."""
        created = _format_date(report.created_at)
        report_type_label = _humanize_report_type(report.report_type)

        parts: list[str] = []
        parts.append("<!DOCTYPE html>")
        parts.append('<html lang="en"><head><meta charset="utf-8">')
        parts.append(
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
        )
        parts.append(f"<title>{_esc(report.title)}</title>")
        parts.append(
            '<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>'
        )
        parts.append("<style>")
        parts.append(self._html_interactive_css())
        parts.append("</style></head><body>")

        # Header
        parts.append('<header class="header">')
        parts.append('<div class="brand">Agentary</div>')
        parts.append(f'<h1>{_esc(report.title)}</h1>')
        if report.description:
            parts.append(f'<p class="subtitle">{_esc(report.description)}</p>')
        parts.append(f'<p class="meta">{report_type_label} &middot; {created}</p>')
        parts.append("</header>")

        parts.append('<main class="content">')

        # Executive summary
        if report.executive_summary:
            parts.append('<div class="executive-summary">')
            parts.append("<h2>Executive Summary</h2>")
            parts.append(_md_to_html(report.executive_summary))
            parts.append("</div>")

        # Methodology
        if report.methodology:
            parts.append("<section><h2>Methodology</h2>")
            parts.append(_md_to_html(report.methodology))
            parts.append("</section>")

        # Sections
        sections = _sorted_sections(report.sections)
        for section in sections:
            parts.append("<section>")
            parts.append(f'<h2>{_esc(section.get("title", ""))}</h2>')
            parts.append(_md_to_html(section.get("content_md", "")))
            parts.append("</section>")

        # Fallback: full content_markdown if no sections
        if not sections and report.content_markdown:
            parts.append("<section>")
            parts.append(_md_to_html(report.content_markdown))
            parts.append("</section>")

        # Interactive charts
        charts = report.charts or []
        if charts:
            parts.append('<section class="charts"><h2>Charts</h2>')
            for chart in charts:
                chart_id = chart.get("id", f"chart_{id(chart)}")
                canvas_id = f"canvas_{chart_id}"
                title = chart.get("title", "")
                parts.append('<div class="chart-container">')
                if title:
                    parts.append(f'<div class="chart-title">{_esc(title)}</div>')
                parts.append(
                    f'<canvas id="{_esc(canvas_id)}" width="600" height="400"></canvas>'
                )
                parts.append("</div>")

                # Chart.js initialization script
                chart_type = chart.get("type", "bar")
                data_json = _json_dumps(chart.get("data", {}))
                options_json = _json_dumps(chart.get("options", {}))
                parts.append("<script>")
                parts.append(
                    f'new Chart(document.getElementById("{_esc(canvas_id)}"), '
                    f'{{"type": "{_esc(chart_type)}", "data": {data_json}, '
                    f'"options": {options_json}}});'
                )
                parts.append("</script>")
            parts.append("</section>")

        # Structured data tables
        if report.structured_data:
            parts.append(self._render_structured_data_html(report.structured_data))

        # Sources
        sources = report.sources or []
        if sources:
            parts.append('<section class="sources"><h2>Sources</h2><ol>')
            for src in sources:
                parts.append(self._render_source_html(src))
            parts.append("</ol></section>")

        parts.append("</main>")
        parts.append("</body></html>")
        return "\n".join(parts)

    def export_to_markdown(self, report: Report) -> str:
        """Return a clean Markdown representation of the report."""
        lines: list[str] = []
        lines.append(f"# {report.title}")
        lines.append("")

        if report.description:
            lines.append(f"*{report.description}*")
            lines.append("")

        report_type_label = _humanize_report_type(report.report_type)
        created = _format_date(report.created_at)
        lines.append(f"**Type:** {report_type_label}  ")
        lines.append(f"**Date:** {created}")
        lines.append("")

        # Executive summary
        if report.executive_summary:
            lines.append("## Executive Summary")
            lines.append("")
            lines.append(report.executive_summary.strip())
            lines.append("")

        # Methodology
        if report.methodology:
            lines.append("## Methodology")
            lines.append("")
            lines.append(report.methodology.strip())
            lines.append("")

        # Sections
        sections = _sorted_sections(report.sections)
        for idx, section in enumerate(sections, start=1):
            title = section.get("title", f"Section {idx}")
            lines.append(f"## {title}")
            lines.append("")
            content = section.get("content_md", "").strip()
            if content:
                lines.append(content)
                lines.append("")

        # Fallback full markdown
        if not sections and report.content_markdown:
            lines.append(report.content_markdown.strip())
            lines.append("")

        # Charts as data tables
        charts = report.charts or []
        if charts:
            lines.append("## Charts")
            lines.append("")
            for chart in charts:
                title = chart.get("title", "Chart")
                lines.append(f"### {title}")
                lines.append("")
                lines.extend(self._chart_to_md_table(chart))
                lines.append("")

        # Structured data
        if report.structured_data:
            lines.extend(self._structured_data_to_md(report.structured_data))

        # Sources
        sources = report.sources or []
        if sources:
            lines.append("## Sources")
            lines.append("")
            for idx, src in enumerate(sources, start=1):
                name = src.get("name", "Unknown")
                url = src.get("url", "")
                src_type = src.get("type", "")
                access_date = src.get("access_date", "")
                entry = f"{idx}. **{name}**"
                if url:
                    entry += f" — [{url}]({url})"
                if src_type:
                    entry += f" [{src_type}]"
                if access_date:
                    entry += f" (accessed {access_date})"
                lines.append(entry)
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Chart rendering (matplotlib)                                       #
    # ------------------------------------------------------------------ #

    def _render_charts_as_images(
        self, charts: list[dict] | None
    ) -> dict[str, str]:
        """Convert Chart.js config dicts to base64 PNG data-URI strings.

        Returns a mapping of ``chart_id`` to a full ``data:image/png;base64,...``
        URI suitable for embedding in ``<img>`` tags.
        """
        if not charts:
            return {}

        images: dict[str, str] = {}
        for chart in charts:
            chart_id = chart.get("id", f"chart_{id(chart)}")
            try:
                b64 = self._render_single_chart(chart)
                images[chart_id] = f"data:image/png;base64,{b64}"
            except Exception:
                logger.warning("Failed to render chart %s", chart_id, exc_info=True)
        return images

    def _render_single_chart(self, chart: dict) -> str:
        """Render one Chart.js config to a base64-encoded PNG string."""
        chart_type = chart.get("type", "bar")
        data = chart.get("data", {})
        labels = data.get("labels", [])
        datasets = data.get("datasets", [])
        title = chart.get("title", "")

        fig, ax = plt.subplots(figsize=(7, 4.5), dpi=150)

        if chart_type == "bar":
            self._draw_bar(ax, labels, datasets)
        elif chart_type == "line":
            self._draw_line(ax, labels, datasets)
        elif chart_type == "pie":
            self._draw_pie(ax, labels, datasets, hollow=False)
        elif chart_type == "doughnut":
            self._draw_pie(ax, labels, datasets, hollow=True)
        elif chart_type == "scatter":
            self._draw_scatter(ax, datasets)
        else:
            # Fallback to bar for unknown types
            self._draw_bar(ax, labels, datasets)

        if title and chart_type not in ("pie", "doughnut"):
            ax.set_title(title, fontsize=13, fontweight="bold", pad=12)

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("ascii")

    # ── Individual chart drawers ────────────────────────────────────── #

    def _draw_bar(
        self,
        ax: plt.Axes,
        labels: list[str],
        datasets: list[dict],
    ) -> None:
        n_datasets = len(datasets)
        x = np.arange(len(labels))
        width = 0.8 / max(n_datasets, 1)
        for i, ds in enumerate(datasets):
            values = ds.get("data", [])
            color = self._pick_color(ds, i)
            offset = (i - (n_datasets - 1) / 2) * width
            ax.bar(x + offset, values, width, label=ds.get("label", ""), color=color)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        if n_datasets > 1:
            ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)

    def _draw_line(
        self,
        ax: plt.Axes,
        labels: list[str],
        datasets: list[dict],
    ) -> None:
        x = np.arange(len(labels))
        for i, ds in enumerate(datasets):
            values = ds.get("data", [])
            color = self._pick_color(ds, i)
            ax.plot(x, values, marker="o", markersize=4, label=ds.get("label", ""), color=color)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    def _draw_pie(
        self,
        ax: plt.Axes,
        labels: list[str],
        datasets: list[dict],
        hollow: bool,
    ) -> None:
        ds = datasets[0] if datasets else {}
        values = ds.get("data", [])
        colors = [self._pick_color({}, i) for i in range(len(values))]
        wedge_props = {"edgecolor": "white", "linewidth": 1.5}
        _wedges, _texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops=wedge_props,
            textprops={"fontsize": 8},
        )
        for at in autotexts:
            at.set_fontsize(7)
        if hollow:
            centre_circle = plt.Circle((0, 0), 0.55, fc="white")
            ax.add_artist(centre_circle)
        ax.set_aspect("equal")

    def _draw_scatter(
        self,
        ax: plt.Axes,
        datasets: list[dict],
    ) -> None:
        for i, ds in enumerate(datasets):
            points = ds.get("data", [])
            color = self._pick_color(ds, i)
            xs = [p.get("x", p[0]) if isinstance(p, (dict, list, tuple)) else 0 for p in points]
            ys = [p.get("y", p[1]) if isinstance(p, (dict, list, tuple)) else 0 for p in points]
            ax.scatter(xs, ys, label=ds.get("label", ""), color=color, s=30)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)

    def _pick_color(self, dataset: dict, index: int) -> str:
        """Return the colour for a dataset, falling back to the palette."""
        bg = dataset.get("backgroundColor")
        if isinstance(bg, str):
            return bg
        return self._CHART_COLORS[index % len(self._CHART_COLORS)]

    # ------------------------------------------------------------------ #
    #  HTML builder (for PDF)                                             #
    # ------------------------------------------------------------------ #

    def _build_html(self, report: Report, chart_images: dict[str, str]) -> str:
        """Assemble the full HTML document used for PDF generation."""
        created = _format_date(report.created_at)
        report_type_label = _humanize_report_type(report.report_type)

        parts: list[str] = []
        parts.append("<!DOCTYPE html>")
        parts.append('<html lang="en"><head><meta charset="utf-8">')
        parts.append(f"<title>{_esc(report.title)}</title>")
        parts.append(f"<style>{self.PDF_CSS}</style>")
        parts.append("</head><body>")

        # ── Cover page ──────────────────────────────────────────────── #
        parts.append('<div class="cover-page">')
        parts.append('<div class="brand">Agentary</div>')
        parts.append(f'<div class="title">{_esc(report.title)}</div>')
        if report.description:
            parts.append(f'<div class="subtitle">{_esc(report.description)}</div>')
        parts.append('<div class="meta">')
        parts.append(f'<div class="date">{created}</div>')
        parts.append(f'<div class="report-type">{report_type_label}</div>')
        parts.append("</div></div>")

        # ── Table of contents ───────────────────────────────────────── #
        sections = _sorted_sections(report.sections)
        toc_items = self._build_toc_items(report, sections)
        if toc_items:
            parts.append('<div class="toc">')
            parts.append("<h2>Table of Contents</h2><ul>")
            for num, title in toc_items:
                parts.append(
                    f'<li><span class="toc-number">{num}.</span> {_esc(title)}</li>'
                )
            parts.append("</ul></div>")

        # ── Executive summary ───────────────────────────────────────── #
        if report.executive_summary:
            parts.append('<div class="section">')
            parts.append("<h2>Executive Summary</h2>")
            parts.append('<div class="executive-summary">')
            parts.append(_md_to_html(report.executive_summary))
            parts.append("</div></div>")

        # ── Methodology ─────────────────────────────────────────────── #
        if report.methodology:
            parts.append('<div class="section">')
            parts.append("<h2>Methodology</h2>")
            parts.append(_md_to_html(report.methodology))
            parts.append("</div>")

        # ── Main sections ───────────────────────────────────────────── #
        for section in sections:
            parts.append('<div class="section">')
            parts.append(f'<h2>{_esc(section.get("title", ""))}</h2>')
            content_md = section.get("content_md", "")
            rendered = _md_to_html(content_md)
            # Inject confidence badges
            rendered = self._inject_confidence_badges(rendered)
            parts.append(rendered)
            parts.append("</div>")

        # Fallback: full content
        if not sections and report.content_markdown:
            parts.append('<div class="section">')
            rendered = _md_to_html(report.content_markdown)
            rendered = self._inject_confidence_badges(rendered)
            parts.append(rendered)
            parts.append("</div>")

        # ── Charts ──────────────────────────────────────────────────── #
        charts = report.charts or []
        if charts:
            parts.append('<div class="section">')
            parts.append("<h2>Charts &amp; Visualizations</h2>")
            for chart in charts:
                chart_id = chart.get("id", f"chart_{id(chart)}")
                title = chart.get("title", "")
                parts.append('<div class="chart-container">')
                if title:
                    parts.append(f'<div class="chart-title">{_esc(title)}</div>')
                data_uri = chart_images.get(chart_id, "")
                if data_uri:
                    parts.append(f'<img src="{data_uri}" alt="{_esc(title)}">')
                else:
                    parts.append("<p><em>Chart could not be rendered.</em></p>")
                parts.append("</div>")
            parts.append("</div>")

        # ── Structured data ─────────────────────────────────────────── #
        if report.structured_data:
            parts.append('<div class="section">')
            parts.append(self._render_structured_data_html(report.structured_data))
            parts.append("</div>")

        # ── Sources ─────────────────────────────────────────────────── #
        sources = report.sources or []
        if sources:
            parts.append('<div class="sources">')
            parts.append("<h2>Sources</h2><ol>")
            for src in sources:
                parts.append(self._render_source_html(src))
            parts.append("</ol></div>")

        parts.append("</body></html>")
        return "\n".join(parts)

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_toc_items(
        report: Report, sections: list[dict]
    ) -> list[tuple[int, str]]:
        """Return numbered (index, title) pairs for the TOC."""
        items: list[tuple[int, str]] = []
        counter = 0
        if report.executive_summary:
            counter += 1
            items.append((counter, "Executive Summary"))
        if report.methodology:
            counter += 1
            items.append((counter, "Methodology"))
        for section in sections:
            counter += 1
            items.append((counter, section.get("title", f"Section {counter}")))
        charts = report.charts or []
        if charts:
            counter += 1
            items.append((counter, "Charts & Visualizations"))
        sources = report.sources or []
        if sources:
            counter += 1
            items.append((counter, "Sources"))
        return items

    @staticmethod
    def _inject_confidence_badges(html: str) -> str:
        """Replace ``[confidence:0.XX]`` tokens with coloured badge spans."""
        import re

        def _badge(match: re.Match) -> str:
            value = float(match.group(1))
            if value >= 0.8:
                level = "high"
            elif value >= 0.5:
                level = "medium"
            else:
                level = "low"
            pct = f"{value * 100:.0f}%"
            return (
                f'<span class="badge badge-{level}"></span>'
                f'<span class="confidence-label">{pct} confidence</span>'
            )

        return re.sub(r"\[confidence:([\d.]+)\]", _badge, html)

    @staticmethod
    def _render_source_html(src: dict) -> str:
        """Render a single source dict as an ``<li>`` element."""
        name = _esc(src.get("name", "Unknown"))
        url = src.get("url", "")
        src_type = src.get("type", "")
        access_date = src.get("access_date", "")

        parts = [f"<li><strong>{name}</strong>"]
        if url:
            parts.append(f' &mdash; <a href="{_esc(url)}">{_esc(url)}</a>')
        if src_type:
            parts.append(f' <span class="source-type">{_esc(src_type)}</span>')
        if access_date:
            parts.append(f' <span class="access-date">accessed {_esc(access_date)}</span>')
        parts.append("</li>")
        return "".join(parts)

    @staticmethod
    def _render_structured_data_html(structured_data: dict | list) -> str:
        """Render structured data (dict or list of dicts) as HTML tables."""
        parts: list[str] = []
        parts.append("<h2>Data</h2>")

        tables: dict[str, list[dict]] = {}
        if isinstance(structured_data, dict):
            for key, value in structured_data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    tables[key] = value
                else:
                    # Single key-value pairs rendered as a simple table
                    tables.setdefault("_overview", [])
                    tables["_overview"].append({"Field": key, "Value": str(value)})
        elif isinstance(structured_data, list) and structured_data:
            if isinstance(structured_data[0], dict):
                tables["Data"] = structured_data

        for table_name, rows in tables.items():
            if not rows:
                continue
            heading = table_name if table_name != "_overview" else "Overview"
            parts.append(f"<h3>{_esc(heading)}</h3>")
            headers = list(rows[0].keys())
            parts.append("<table><thead><tr>")
            for h in headers:
                parts.append(f"<th>{_esc(str(h))}</th>")
            parts.append("</tr></thead><tbody>")
            for row in rows:
                parts.append("<tr>")
                for h in headers:
                    cell = row.get(h, "")
                    parts.append(f"<td>{_esc(str(cell))}</td>")
                parts.append("</tr>")
            parts.append("</tbody></table>")

        return "\n".join(parts)

    def _chart_to_md_table(self, chart: dict) -> list[str]:
        """Convert a Chart.js config to a Markdown table."""
        lines: list[str] = []
        data = chart.get("data", {})
        labels = data.get("labels", [])
        datasets = data.get("datasets", [])

        if not labels and not datasets:
            lines.append("*No data available.*")
            return lines

        # Build header
        header_cols = ["Label"] + [ds.get("label", f"Dataset {i+1}") for i, ds in enumerate(datasets)]
        lines.append("| " + " | ".join(header_cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(header_cols)) + " |")

        for idx, label in enumerate(labels):
            row_vals = [str(label)]
            for ds in datasets:
                ds_data = ds.get("data", [])
                val = ds_data[idx] if idx < len(ds_data) else ""
                row_vals.append(str(val))
            lines.append("| " + " | ".join(row_vals) + " |")

        return lines

    def _structured_data_to_md(self, structured_data: dict | list) -> list[str]:
        """Convert structured data to Markdown tables."""
        lines: list[str] = []
        lines.append("## Data")
        lines.append("")

        tables: dict[str, list[dict]] = {}
        if isinstance(structured_data, dict):
            for key, value in structured_data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    tables[key] = value
                else:
                    tables.setdefault("_overview", [])
                    tables["_overview"].append({"Field": key, "Value": str(value)})
        elif isinstance(structured_data, list) and structured_data:
            if isinstance(structured_data[0], dict):
                tables["Data"] = structured_data

        for table_name, rows in tables.items():
            if not rows:
                continue
            heading = table_name if table_name != "_overview" else "Overview"
            lines.append(f"### {heading}")
            lines.append("")
            headers = list(rows[0].keys())
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for row in rows:
                vals = [str(row.get(h, "")) for h in headers]
                lines.append("| " + " | ".join(vals) + " |")
            lines.append("")

        return lines

    @staticmethod
    def _html_interactive_css() -> str:
        """CSS for the standalone interactive HTML export."""
        return """
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #222;
            max-width: 900px;
            margin: 0 auto;
            padding: 24px;
            background: #fafafa;
        }
        .header {
            text-align: center;
            padding: 40px 0 24px;
            border-bottom: 2px solid #e0e0e0;
            margin-bottom: 32px;
        }
        .brand {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 4px;
            color: #6c63ff;
            margin-bottom: 12px;
        }
        h1 { font-size: 28px; color: #1a1a2e; margin-bottom: 8px; }
        h2 { font-size: 20px; color: #16213e; margin-top: 32px; margin-bottom: 12px; border-bottom: 1px solid #e0e0e0; padding-bottom: 6px; }
        h3 { font-size: 16px; color: #1a1a2e; margin-top: 20px; margin-bottom: 8px; }
        .subtitle { font-size: 14px; color: #555; }
        .meta { font-size: 12px; color: #888; margin-top: 8px; }
        .content { background: #fff; padding: 32px; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
        .executive-summary {
            background: #f8f9ff;
            border-left: 4px solid #6c63ff;
            padding: 16px 20px;
            margin: 16px 0;
            border-radius: 0 4px 4px 0;
        }
        table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }
        thead th { background: #1a1a2e; color: #fff; padding: 10px 12px; text-align: left; }
        tbody td { padding: 8px 12px; border-bottom: 1px solid #e0e0e0; }
        tbody tr:nth-child(even) { background: #f9f9fb; }
        .chart-container { text-align: center; margin: 20px 0; }
        .chart-container canvas { max-width: 100%; }
        .chart-title { font-size: 14px; font-weight: 600; color: #333; margin-bottom: 8px; }
        .sources ol { padding-left: 20px; }
        .sources li { margin-bottom: 8px; font-size: 14px; }
        blockquote { border-left: 3px solid #d1d5db; margin: 12px 0; padding: 8px 16px; color: #555; font-style: italic; background: #fafafa; }
        pre { background: #f4f4f8; padding: 12px 16px; border-radius: 4px; font-size: 13px; overflow-x: auto; border: 1px solid #e0e0e0; }
        code { font-family: "Courier New", Courier, monospace; font-size: 13px; }
        a { color: #2563eb; text-decoration: none; }
        a:hover { text-decoration: underline; }
        ul, ol { margin: 8px 0; padding-left: 24px; }
        li { margin-bottom: 4px; }

        @media (max-width: 640px) {
            body { padding: 12px; }
            .content { padding: 16px; }
            h1 { font-size: 22px; }
        }
        """


# ====================================================================== #
#  Module-level helpers (pure functions, no state)                        #
# ====================================================================== #


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _md_to_html(text: str) -> str:
    """Convert Markdown text to HTML using markdown2."""
    if not text:
        return ""
    return markdown2.markdown(
        text,
        extras=[
            "fenced-code-blocks",
            "tables",
            "header-ids",
            "task_list",
            "strike",
            "cuddled-lists",
        ],
    )


def _format_date(dt: datetime | None) -> str:
    """Format a datetime for display, with a safe fallback."""
    if dt is None:
        return "N/A"
    try:
        return dt.strftime("%B %d, %Y")
    except Exception:
        return str(dt)


def _humanize_report_type(report_type: str | None) -> str:
    """Turn a snake_case report type into a human-readable label."""
    if not report_type:
        return "Report"
    return report_type.replace("_", " ").title()


def _sorted_sections(sections: list[dict] | None) -> list[dict]:
    """Return sections sorted by their ``order`` key."""
    if not sections:
        return []
    return sorted(sections, key=lambda s: s.get("order", 0))


def _json_dumps(obj: object) -> str:
    """Serialize to JSON, handling non-serializable values gracefully."""
    import json

    try:
        return json.dumps(obj, default=str)
    except (TypeError, ValueError):
        return "{}"
