"""Chart generator that produces Chart.js configuration objects from structured data."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from google import genai

from ...config import settings

logger = logging.getLogger(__name__)


class ChartGenerator:
    """Generates Chart.js configuration objects from data."""

    COLORS = [
        "#4F46E5",
        "#7C3AED",
        "#2563EB",
        "#0891B2",
        "#059669",
        "#D97706",
        "#DC2626",
        "#EC4899",
    ]
    BG_COLORS_ALPHA = [
        "rgba(79,70,229,0.6)",
        "rgba(124,58,237,0.6)",
        "rgba(37,99,235,0.6)",
        "rgba(8,145,178,0.6)",
        "rgba(5,150,105,0.6)",
        "rgba(217,119,6,0.6)",
        "rgba(220,38,38,0.6)",
        "rgba(236,72,153,0.6)",
    ]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _slugify(title: str) -> str:
        """Convert a title into a lowercase underscore-separated id."""
        slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
        return slug

    def _pick_colors(self, count: int) -> list[str]:
        """Return *count* colours, cycling through the palette as needed."""
        return [self.COLORS[i % len(self.COLORS)] for i in range(count)]

    def _pick_bg_colors(self, count: int) -> list[str]:
        return [self.BG_COLORS_ALPHA[i % len(self.BG_COLORS_ALPHA)] for i in range(count)]

    @staticmethod
    def _base_options(title: str, *, legend: bool = True) -> dict[str, Any]:
        return {
            "responsive": True,
            "plugins": {
                "title": {"display": True, "text": title},
                "legend": {"display": legend},
            },
        }

    # ------------------------------------------------------------------
    # Auto-generate via Gemini
    # ------------------------------------------------------------------

    async def auto_generate_charts(
        self,
        structured_data: dict,
        context: str,
    ) -> list[dict]:
        """Use Gemini to analyse structured data and decide what deserves visualisation.

        Prompts Gemini with *structured_data* and *context*, asking it to return
        a JSON array of chart specs.  For each spec the appropriate chart-builder
        method is called.

        Returns an empty list when the API key is missing or Gemini fails.
        """
        if not settings.gemini_api_key:
            return []

        prompt = (
            "You are a data-visualisation expert. "
            "Given the following structured data and context, decide which charts "
            "would be most informative. Return ONLY a JSON array of chart spec objects.\n\n"
            "Each spec object must have:\n"
            '  - "chart_type": one of "bar", "line", "histogram", "pie", "scatter", "multi_line", "map"\n'
            '  - "title": a short descriptive chart title\n'
            '  - "params": an object with the parameters needed for the chart method '
            "(see descriptions below)\n\n"
            "Chart method signatures and their params:\n"
            '  bar      → items (list of dicts), value_field (str), label_field (str)\n'
            '  line     → timeseries (list of dicts with date & value), date_field, value_field\n'
            '  histogram→ values (list of numbers), bins (int, optional)\n'
            '  pie      → categories (object mapping category name → number)\n'
            '  scatter  → points (list of dicts), x_field, y_field, label_field\n'
            '  multi_line → series (object mapping series name → list of dicts), date_field, value_field\n'
            '  map      → locations (list of dicts with lat, lng, label)\n\n'
            f"Context: {context}\n\n"
            f"Data:\n{json.dumps(structured_data, default=str)}\n"
        )

        try:
            client = genai.Client(api_key=settings.gemini_api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )

            specs: list[dict] = json.loads(response.text)
            if not isinstance(specs, list):
                specs = [specs]
        except Exception:
            logger.exception("Gemini chart-spec generation failed")
            return []

        charts: list[dict] = []
        for spec in specs:
            chart_type = spec.get("chart_type", "")
            title = spec.get("title", "Chart")
            params = spec.get("params", {})

            try:
                chart = self._build_chart_from_spec(chart_type, title, params)
                if chart is not None:
                    charts.append(chart)
            except Exception:
                logger.exception("Failed to build chart from spec: %s", spec)

        return charts

    def _build_chart_from_spec(
        self,
        chart_type: str,
        title: str,
        params: dict,
    ) -> dict | None:
        """Dispatch a single Gemini spec to the correct builder method."""
        if chart_type == "bar":
            return self.comparison_bar_chart(
                items=params["items"],
                value_field=params["value_field"],
                label_field=params["label_field"],
                title=title,
            )
        if chart_type == "line":
            return self.trend_line_chart(
                timeseries=params["timeseries"],
                date_field=params["date_field"],
                value_field=params["value_field"],
                title=title,
            )
        if chart_type == "histogram":
            return self.distribution_histogram(
                values=params["values"],
                title=title,
                bins=params.get("bins", 10),
            )
        if chart_type == "pie":
            return self.pie_chart(categories=params["categories"], title=title)
        if chart_type == "scatter":
            return self.scatter_plot(
                points=params["points"],
                x_field=params["x_field"],
                y_field=params["y_field"],
                label_field=params["label_field"],
                title=title,
            )
        if chart_type == "multi_line":
            return self.multi_series_line(
                series=params["series"],
                date_field=params["date_field"],
                value_field=params["value_field"],
                title=title,
            )
        if chart_type == "map":
            return self.generate_map_pins(locations=params["locations"])

        logger.warning("Unknown chart_type: %s", chart_type)
        return None

    # ------------------------------------------------------------------
    # Individual chart builders
    # ------------------------------------------------------------------

    def comparison_bar_chart(
        self,
        items: list[dict],
        value_field: str,
        label_field: str,
        title: str,
    ) -> dict:
        """Create a bar chart comparing items on a metric."""
        labels = [item.get(label_field, "") for item in items]
        data_values = [item.get(value_field, 0) for item in items]
        count = len(labels)

        return {
            "id": self._slugify(title),
            "type": "bar",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": title,
                        "data": data_values,
                        "backgroundColor": self._pick_bg_colors(count),
                        "borderColor": self._pick_colors(count),
                        "borderWidth": 1,
                    }
                ],
            },
            "options": self._base_options(title),
        }

    def trend_line_chart(
        self,
        timeseries: list[dict],
        date_field: str,
        value_field: str,
        title: str,
    ) -> dict:
        """Create a line chart showing a trend over time."""
        sorted_series = sorted(timeseries, key=lambda d: d.get(date_field, ""))
        labels = [entry.get(date_field, "") for entry in sorted_series]
        data_values = [entry.get(value_field, 0) for entry in sorted_series]

        return {
            "id": self._slugify(title),
            "type": "line",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": title,
                        "data": data_values,
                        "backgroundColor": self.BG_COLORS_ALPHA[0],
                        "borderColor": self.COLORS[0],
                        "borderWidth": 2,
                        "fill": False,
                        "tension": 0.3,
                    }
                ],
            },
            "options": self._base_options(title),
        }

    def distribution_histogram(
        self,
        values: list[float],
        title: str,
        bins: int = 10,
    ) -> dict:
        """Create a histogram showing value distribution.

        Buckets the raw *values* into *bins* equally-spaced ranges and returns
        a bar-chart config representing the frequency of each bucket.
        """
        if not values:
            return {
                "id": self._slugify(title),
                "type": "bar",
                "title": title,
                "data": {"labels": [], "datasets": [{"label": title, "data": [], "backgroundColor": [], "borderColor": [], "borderWidth": 1}]},
                "options": self._base_options(title, legend=False),
            }

        min_val = min(values)
        max_val = max(values)

        # Avoid division by zero when all values are identical
        if min_val == max_val:
            return {
                "id": self._slugify(title),
                "type": "bar",
                "title": title,
                "data": {
                    "labels": [str(min_val)],
                    "datasets": [
                        {
                            "label": title,
                            "data": [len(values)],
                            "backgroundColor": [self.BG_COLORS_ALPHA[0]],
                            "borderColor": [self.COLORS[0]],
                            "borderWidth": 1,
                        }
                    ],
                },
                "options": self._base_options(title, legend=False),
            }

        bin_width = (max_val - min_val) / bins
        bucket_counts = [0] * bins
        for v in values:
            idx = int((v - min_val) / bin_width)
            if idx >= bins:
                idx = bins - 1
            bucket_counts[idx] += 1

        labels = [
            f"{min_val + i * bin_width:.1f}-{min_val + (i + 1) * bin_width:.1f}"
            for i in range(bins)
        ]

        return {
            "id": self._slugify(title),
            "type": "bar",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": title,
                        "data": bucket_counts,
                        "backgroundColor": self._pick_bg_colors(bins),
                        "borderColor": self._pick_colors(bins),
                        "borderWidth": 1,
                    }
                ],
            },
            "options": self._base_options(title, legend=False),
        }

    def pie_chart(self, categories: dict[str, float], title: str) -> dict:
        """Create a pie chart from a category-to-value mapping."""
        labels = list(categories.keys())
        data_values = list(categories.values())
        count = len(labels)

        return {
            "id": self._slugify(title),
            "type": "pie",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": title,
                        "data": data_values,
                        "backgroundColor": self._pick_bg_colors(count),
                        "borderColor": self._pick_colors(count),
                        "borderWidth": 1,
                    }
                ],
            },
            "options": self._base_options(title),
        }

    def scatter_plot(
        self,
        points: list[dict],
        x_field: str,
        y_field: str,
        label_field: str,
        title: str,
    ) -> dict:
        """Create a scatter plot (e.g., price vs sqft for properties)."""
        data_points = [
            {"x": pt.get(x_field, 0), "y": pt.get(y_field, 0)}
            for pt in points
        ]
        point_labels = [pt.get(label_field, "") for pt in points]

        return {
            "id": self._slugify(title),
            "type": "scatter",
            "title": title,
            "data": {
                "labels": point_labels,
                "datasets": [
                    {
                        "label": title,
                        "data": data_points,
                        "backgroundColor": self.BG_COLORS_ALPHA[0],
                        "borderColor": self.COLORS[0],
                        "borderWidth": 1,
                    }
                ],
            },
            "options": {
                **self._base_options(title),
                "scales": {
                    "x": {
                        "type": "linear",
                        "title": {"display": True, "text": x_field},
                    },
                    "y": {
                        "type": "linear",
                        "title": {"display": True, "text": y_field},
                    },
                },
            },
        }

    def multi_series_line(
        self,
        series: dict[str, list[dict]],
        date_field: str,
        value_field: str,
        title: str,
    ) -> dict:
        """Multiple lines on one chart (e.g., price trends for different areas)."""
        # Collect all unique dates across every series for a shared x-axis
        all_dates: set[str] = set()
        sorted_series_data: dict[str, list[dict]] = {}
        for name, entries in series.items():
            sorted_entries = sorted(entries, key=lambda d: d.get(date_field, ""))
            sorted_series_data[name] = sorted_entries
            for entry in sorted_entries:
                all_dates.add(str(entry.get(date_field, "")))

        labels = sorted(all_dates)

        datasets: list[dict[str, Any]] = []
        for idx, (name, entries) in enumerate(sorted_series_data.items()):
            # Build a lookup so each series aligns to the shared labels
            date_to_value = {
                str(e.get(date_field, "")): e.get(value_field, 0)
                for e in entries
            }
            data_values = [date_to_value.get(d, None) for d in labels]
            color = self.COLORS[idx % len(self.COLORS)]

            datasets.append({
                "label": name,
                "data": data_values,
                "backgroundColor": self.BG_COLORS_ALPHA[idx % len(self.BG_COLORS_ALPHA)],
                "borderColor": color,
                "borderWidth": 2,
                "fill": False,
                "tension": 0.3,
            })

        return {
            "id": self._slugify(title),
            "type": "line",
            "title": title,
            "data": {
                "labels": labels,
                "datasets": datasets,
            },
            "options": self._base_options(title),
        }

    def generate_map_pins(self, locations: list[dict]) -> dict:
        """Generate data for a map visualisation (lat/lng pins with labels).

        Returns a dict with type ``"map"`` and a ``pins`` list rather than a
        standard Chart.js dataset, since maps are rendered by a different
        front-end component (e.g., Leaflet / Google Maps).
        """
        pins = [
            {
                "lat": loc.get("lat", 0),
                "lng": loc.get("lng", 0),
                "label": loc.get("label", ""),
                **{k: v for k, v in loc.items() if k not in ("lat", "lng", "label")},
            }
            for loc in locations
        ]

        return {
            "id": "map_pins",
            "type": "map",
            "title": "Map",
            "data": {
                "pins": pins,
            },
            "options": {
                "responsive": True,
                "plugins": {
                    "title": {"display": True, "text": "Map"},
                    "legend": {"display": False},
                },
            },
        }
