"""Celery application for background task execution."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

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
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Recycle each worker process after N tasks so accumulated heap (LLM
    # context, finding lists, logging contexts that workers do not free
    # between tasks) is released. Without this, a research-heavy worker
    # grows several GB of RSS over a day. See PERF review #7.
    worker_max_tasks_per_child=10,
    # Soft + hard time limits on every task. Without these, a Celery worker
    # can hang indefinitely on a stuck HTTP call (Gemini latency spikes,
    # Twilio webhook timeouts) and block its queue.
    task_soft_time_limit=300,  # 5 min — task can clean up
    task_time_limit=360,  # 6 min — SIGKILL
    task_default_queue="default",
    task_routes={
        "app.tasks.crew_tasks.*": {"queue": "research"},
        "app.tasks.mission_runs.*": {"queue": "missions"},
        "app.tasks.research_tasks.*": {"queue": "research"},
        "app.tasks.voice_tasks.*": {"queue": "voice"},
        "app.tasks.monitor_tasks.*": {"queue": "monitors"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
        "app.tasks.workflow_tasks.*": {"queue": "workflows"},
        "app.tasks.analytics_tasks.*": {"queue": "analytics"},
        "app.tasks.signal_tasks.*": {"queue": "signals"},
        "app.tasks.migration_tasks.*": {"queue": "migrations"},
        "app.tasks.insight_tasks.*": {"queue": "signals"},
        "app.tasks.action_tasks.*": {"queue": "actions"},
    },
    beat_schedule={
        "check-monitors-every-5m": {
            "task": "app.tasks.monitor_tasks.check_all_monitors",
            "schedule": 300.0,
        },
        "mark-stale-insights-daily": {
            "task": "app.tasks.insight_tasks.mark_stale_insights",
            "schedule": crontab(hour=2, minute=0),
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
    "app.tasks.signal_tasks",
    "app.tasks.migration_tasks",
    "app.tasks.insight_tasks",
    "app.tasks.action_tasks",
])
