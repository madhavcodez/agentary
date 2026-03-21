"""Celery application for background task execution."""
from __future__ import annotations

from celery import Celery

from .config import settings

celery_app = Celery(
    "agentary",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    task_routes={
        "app.tasks.crew_tasks.*": {"queue": "research"},
        "app.tasks.mission_runs.*": {"queue": "research"},
        "app.tasks.research_tasks.*": {"queue": "research"},
        "app.tasks.voice_tasks.*": {"queue": "voice"},
        "app.tasks.monitor_tasks.*": {"queue": "monitors"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
    },
    beat_schedule={
        "check-monitors-every-5m": {
            "task": "app.tasks.monitor_tasks.check_all_monitors",
            "schedule": 300.0,
        },
    },
)

# Auto-discover tasks in all task modules
celery_app.autodiscover_tasks([
    "app.tasks.crew_tasks",
    "app.tasks.mission_runs",
    "app.tasks.research_tasks",
    "app.tasks.voice_tasks",
    "app.tasks.monitor_tasks",
    "app.tasks.report_tasks",
])
