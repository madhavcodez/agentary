from __future__ import annotations

import asyncio
import contextlib
import logging
from datetime import datetime
from uuid import UUID

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

# Job ID prefix for per-user autopilot jobs
_AUTOPILOT_JOB_PREFIX = "autopilot_user_"


def _run_ingest():
    from .ingest.runner import run_all_connectors

    session = SessionLocal()
    try:
        count = asyncio.run(run_all_connectors(session))
        logger.info("Scheduled ingest completed: %d new opportunities", count)
    except Exception as e:
        logger.error("Scheduled ingest failed: %s", e)
    finally:
        session.close()


def _run_scoring():
    from .match_engine import score_all_matches

    session = SessionLocal()
    try:
        result = asyncio.run(score_all_matches(session))
        logger.info("Scheduled scoring completed: %s", result)
    except Exception as e:
        logger.error("Scheduled scoring failed: %s", e)
    finally:
        session.close()


def _is_business_hours(timezone_name: str) -> bool:
    """Check whether the current time is within business hours (8AM-6PM weekdays)."""
    try:
        tz = pytz.timezone(timezone_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone("America/Los_Angeles")

    now = datetime.now(tz)
    # Monday=0 .. Sunday=6
    if now.weekday() >= 5:
        return False
    return 8 <= now.hour < 18


def _run_autopilot_for_user(user_id: str):
    """Execute an autopilot cycle scoped to a single user.

    Respects business-hours-only preference before running.
    """
    from .autopilot import run_autopilot_cycle

    session = SessionLocal()
    try:
        from ..models.user import User

        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning("Autopilot job for unknown user %s — removing job", user_id)
            remove_autopilot_job(user_id)
            return

        if not user.autopilot_enabled:
            logger.info("Autopilot disabled for user %s — skipping", user_id)
            return

        if user.autopilot_business_hours_only and not _is_business_hours(user.autopilot_timezone):
            logger.info(
                "Outside business hours for user %s (tz=%s) — skipping",
                user_id,
                user.autopilot_timezone,
            )
            return

        result = asyncio.run(run_autopilot_cycle(session, user_id))
        logger.info("Autopilot cycle completed for user %s: %s", user_id, result)
    except Exception as e:
        logger.error("Autopilot cycle failed for user %s: %s", user_id, e)
    finally:
        session.close()


def _autopilot_job_id(user_id: str | UUID) -> str:
    """Build a deterministic job ID for a user's autopilot schedule."""
    return f"{_AUTOPILOT_JOB_PREFIX}{user_id}"


def add_autopilot_job(user_id: str | UUID, cron_expr: str, timezone: str) -> None:
    """Add (or replace) an APScheduler CronTrigger job for a user's autopilot.

    Args:
        user_id: The user's UUID (string or UUID).
        cron_expr: Cron expression like "0 9 * * 1-5".
        timezone: IANA timezone string like "America/Los_Angeles".
    """
    job_id = _autopilot_job_id(user_id)

    # Parse cron fields: minute hour day_of_month month day_of_week
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"Invalid cron expression '{cron_expr}': expected 5 fields "
            "(minute hour day month day_of_week)"
        )

    try:
        tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone("America/Los_Angeles")

    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone=tz,
    )

    scheduler.add_job(
        _run_autopilot_for_user,
        trigger,
        args=[str(user_id)],
        id=job_id,
        replace_existing=True,
    )
    logger.info(
        "Autopilot job scheduled for user %s: cron=%s tz=%s",
        user_id,
        cron_expr,
        timezone,
    )


def remove_autopilot_job(user_id: str | UUID) -> None:
    """Remove a user's autopilot job if it exists."""
    job_id = _autopilot_job_id(user_id)
    # Job may not exist; that's fine
    with contextlib.suppress(Exception):
        scheduler.remove_job(job_id)
        logger.info("Autopilot job removed for user %s", user_id)


def load_all_autopilot_jobs() -> None:
    """Load autopilot jobs for all users with autopilot_enabled=True.

    Called once at app startup.
    """
    session = SessionLocal()
    try:
        from ..models.user import User

        users = (
            session.query(User)
            .filter(
                User.autopilot_enabled == True,  # noqa: E712
                User.autopilot_cron.isnot(None),
            )
            .all()
        )
        for user in users:
            try:
                add_autopilot_job(
                    user_id=str(user.id),
                    cron_expr=user.autopilot_cron,
                    timezone=user.autopilot_timezone,
                )
            except Exception as e:
                logger.error("Failed to load autopilot job for user %s: %s", user.id, e)
        logger.info("Loaded autopilot jobs for %d users", len(users))
    except Exception as e:
        logger.error("Failed to load autopilot jobs: %s", e)
    finally:
        session.close()


# ── Monitor scheduled checks ────────────────────────────────────────

_MONITOR_JOB_PREFIX = "monitor_"


def _monitor_job_id(monitor_id: str | UUID) -> str:
    return f"{_MONITOR_JOB_PREFIX}{monitor_id}"


def _run_monitor_check(monitor_id: str):
    """Execute a scheduled monitor check."""
    from .monitor_service import execute_check

    try:
        asyncio.run(execute_check(monitor_id))
    except Exception as e:
        logger.error("Scheduled monitor check failed for %s: %s", monitor_id, e)


def add_monitor_job(monitor_id: str | UUID, cron_expr: str, timezone_name: str = "UTC") -> None:
    """Add (or replace) a scheduled monitor check job."""
    job_id = _monitor_job_id(monitor_id)

    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression '{cron_expr}': expected 5 fields")

    try:
        tz = pytz.timezone(timezone_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone("UTC")

    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone=tz,
    )

    scheduler.add_job(
        _run_monitor_check,
        trigger,
        args=[str(monitor_id)],
        id=job_id,
        replace_existing=True,
    )
    logger.info("Monitor job scheduled: id=%s cron=%s tz=%s", monitor_id, cron_expr, timezone_name)


def remove_monitor_job(monitor_id: str | UUID) -> None:
    """Remove a monitor's scheduled job."""
    job_id = _monitor_job_id(monitor_id)
    with contextlib.suppress(Exception):
        scheduler.remove_job(job_id)
        logger.info("Monitor job removed: %s", monitor_id)


def load_all_monitor_jobs() -> None:
    """Load scheduled jobs for all active monitors at startup."""
    session = SessionLocal()
    try:
        from ..models.monitor import Monitor

        monitors = (
            session.query(Monitor)
            .filter(
                Monitor.status == "active",
                Monitor.schedule_cron.isnot(None),
            )
            .all()
        )
        for m in monitors:
            try:
                add_monitor_job(str(m.id), m.schedule_cron, m.timezone)
            except Exception as e:
                logger.error("Failed to load monitor job %s: %s", m.id, e)
        logger.info("Loaded monitor jobs for %d monitors", len(monitors))
    except Exception as e:
        logger.error("Failed to load monitor jobs: %s", e)
    finally:
        session.close()


## ── Workflow scheduled runs ─────────────────────────────────────────

_WORKFLOW_JOB_PREFIX = "workflow_"


def _workflow_job_id(workflow_id: str | UUID) -> str:
    return f"{_WORKFLOW_JOB_PREFIX}{workflow_id}"


def _run_scheduled_workflow(workflow_id: str):
    """Execute a scheduled workflow run."""
    from ..models.workflow import Workflow
    from .workflow.service import trigger_run as wf_trigger_run

    session = SessionLocal()
    try:
        workflow = session.query(Workflow).filter(Workflow.id == workflow_id).first()
        if not workflow:
            logger.warning("Scheduled workflow %s not found — removing job", workflow_id)
            remove_workflow_schedule(workflow_id)
            return
        if workflow.status != "active":
            logger.info("Workflow %s not active — skipping scheduled run", workflow_id)
            return
        asyncio.run(wf_trigger_run(session, workflow, trigger="scheduled"))
        logger.info("Scheduled workflow run completed for %s", workflow_id)
    except Exception as e:
        logger.error("Scheduled workflow run failed for %s: %s", workflow_id, e)
    finally:
        session.close()


def add_workflow_schedule(
    workflow_id: str | UUID, cron_expr: str, timezone_name: str = "America/Los_Angeles"
) -> None:
    """Add (or replace) a scheduled workflow run job."""
    job_id = _workflow_job_id(workflow_id)
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression '{cron_expr}': expected 5 fields")

    try:
        tz = pytz.timezone(timezone_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone("America/Los_Angeles")

    trigger = CronTrigger(
        minute=parts[0],
        hour=parts[1],
        day=parts[2],
        month=parts[3],
        day_of_week=parts[4],
        timezone=tz,
    )
    scheduler.add_job(
        _run_scheduled_workflow,
        trigger,
        args=[str(workflow_id)],
        id=job_id,
        replace_existing=True,
    )
    logger.info(
        "Workflow job scheduled: id=%s cron=%s tz=%s", workflow_id, cron_expr, timezone_name
    )


def remove_workflow_schedule(workflow_id: str | UUID) -> None:
    """Remove a workflow's scheduled job."""
    job_id = _workflow_job_id(workflow_id)
    with contextlib.suppress(Exception):
        scheduler.remove_job(job_id)
        logger.info("Workflow job removed: %s", workflow_id)


def load_all_workflow_schedules() -> None:
    """Load scheduled jobs for all active scheduled workflows at startup."""
    session = SessionLocal()
    try:
        from ..models.workflow import Workflow

        workflows = (
            session.query(Workflow)
            .filter(
                Workflow.status == "active",
                Workflow.trigger_type == "scheduled",
                Workflow.trigger_config.isnot(None),
            )
            .all()
        )
        for wf in workflows:
            try:
                config = wf.trigger_config or {}
                add_workflow_schedule(
                    str(wf.id),
                    config.get("cron", "0 9 * * *"),
                    config.get("timezone", "America/Los_Angeles"),
                )
            except Exception as e:
                logger.error("Failed to load workflow schedule %s: %s", wf.id, e)
        logger.info("Loaded workflow schedules for %d workflows", len(workflows))
    except Exception as e:
        logger.error("Failed to load workflow schedules: %s", e)
    finally:
        session.close()


def start_scheduler():
    scheduler.add_job(_run_ingest, "interval", hours=6, id="ingest_job", replace_existing=True)
    scheduler.add_job(_run_scoring, "interval", hours=24, id="scoring_job", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started: ingest every 6h, scoring every 24h")

    # Load per-user autopilot schedules
    load_all_autopilot_jobs()

    # Load monitor schedules
    load_all_monitor_jobs()

    # Load workflow schedules
    load_all_workflow_schedules()

    # Seed system workflow templates
    from .workflow.templates import seed_templates

    session = SessionLocal()
    try:
        seed_templates(session)
    except Exception as e:
        logger.error("Failed to seed workflow templates: %s", e)
    finally:
        session.close()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
