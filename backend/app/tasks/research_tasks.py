from __future__ import annotations

from .celery_app import celery_app


@celery_app.task(name="app.tasks.research_tasks.run_research")
def run_research(mission_id: str, query: str) -> dict:
    """Run a research task. Stub."""
    return {"status": "not_implemented"}
