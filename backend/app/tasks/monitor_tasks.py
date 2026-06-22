from __future__ import annotations

from .celery_app import celery_app


@celery_app.task(name="app.tasks.monitor_tasks.check_monitor")
def check_monitor(monitor_id: str) -> dict:
    """Check a single monitor. Stub."""
    return {"status": "not_implemented"}


@celery_app.task(name="app.tasks.monitor_tasks.check_all_monitors")
def check_all_monitors() -> dict:
    """Check all active monitors. Stub."""
    return {"status": "not_implemented"}
