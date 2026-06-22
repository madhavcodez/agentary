from __future__ import annotations

from .celery_app import celery_app


@celery_app.task(name="app.tasks.report_tasks.generate_report")
def generate_report(report_id: str) -> dict:
    """Generate a report. Stub."""
    return {"status": "not_implemented"}
