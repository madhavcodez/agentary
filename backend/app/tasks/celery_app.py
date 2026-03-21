from __future__ import annotations

import os

from celery import Celery

# Redis URL from env, default to localhost
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "agentary",
    broker=REDIS_URL,
    backend=REDIS_URL,
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
    task_routes={
        "app.tasks.mission_runs.*": {"queue": "missions"},
        "app.tasks.research_tasks.*": {"queue": "research"},
        "app.tasks.voice_tasks.*": {"queue": "voice"},
        "app.tasks.monitor_tasks.*": {"queue": "monitors"},
        "app.tasks.report_tasks.*": {"queue": "reports"},
        "app.tasks.workflow_tasks.*": {"queue": "workflows"},
        "app.tasks.analytics_tasks.*": {"queue": "analytics"},
    },
    beat_schedule={
        # Stub — will be populated in later phases
        # "check-monitors": {
        #     "task": "app.tasks.monitor_tasks.check_all_monitors",
        #     "schedule": 300.0,  # every 5 minutes
        # },
    },
)

# Auto-discover tasks in the tasks package
celery_app.autodiscover_tasks(["app.tasks"])
