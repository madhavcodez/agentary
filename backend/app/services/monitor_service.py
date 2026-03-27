"""Monitor service: create, execute checks, detect changes, send alerts."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from ..core.events import Event, EventType, event_bus
from ..models.enums import FailureCategory, RunStatus
from ..models.monitor import Alert, Monitor
from ..models.monitor_run import MonitorRun
from .change_detector import (
    ChangeResult,
    detect_new_items,
    detect_removed_items,
    detect_text_change,
    detect_value_change,
)
from .state_machine import transition as sm_transition, InvalidTransition

logger = logging.getLogger(__name__)

# Default cooldown period for alert deduplication (seconds)
DEFAULT_ALERT_COOLDOWN_SECONDS: int = 3600


def _transition_monitor_run(
    monitor_run: MonitorRun,
    target: RunStatus,
    reason: str | None = None,
) -> None:
    """Validate and apply a state transition on a MonitorRun."""
    current_str = monitor_run.status.value if hasattr(monitor_run.status, 'value') else str(monitor_run.status)
    current = RunStatus(current_str)
    record = sm_transition(current, target, reason)
    monitor_run.status = target
    transitions = list(monitor_run.state_transitions or [])
    transitions.append(record)
    monitor_run.state_transitions = transitions


# ── CRUD ────────────────────────────────────────────────────────────

def create_monitor(db: Session, user_id: UUID, data: dict[str, Any]) -> Monitor:
    """Create a new monitor and register its schedule."""
    monitor = Monitor(
        user_id=user_id,
        project_id=data.get("project_id"),
        name=data["name"],
        description=data.get("description"),
        monitor_type=data["monitor_type"],
        status=data.get("status", "active"),
        check_config=data.get("check_config", {}),
        alert_config=data.get("alert_config", {}),
        schedule_cron=data.get("schedule_cron"),
        timezone=data.get("timezone", "UTC"),
    )
    db.add(monitor)
    db.commit()
    db.refresh(monitor)

    # Register with scheduler
    if monitor.schedule_cron and monitor.status == "active":
        from .scheduler import add_monitor_job

        add_monitor_job(
            monitor_id=str(monitor.id),
            cron_expr=monitor.schedule_cron,
            timezone_name=monitor.timezone,
        )

    return monitor


def update_monitor(db: Session, monitor: Monitor, data: dict[str, Any]) -> Monitor:
    """Update a monitor and re-register its schedule if cron changed."""
    for field in ("name", "description", "monitor_type", "check_config",
                  "alert_config", "schedule_cron", "timezone"):
        if field in data:
            setattr(monitor, field, data[field])
    db.commit()
    db.refresh(monitor)

    # Re-register schedule
    from .scheduler import add_monitor_job, remove_monitor_job

    if monitor.schedule_cron and monitor.status == "active":
        add_monitor_job(str(monitor.id), monitor.schedule_cron, monitor.timezone)
    else:
        remove_monitor_job(str(monitor.id))

    return monitor


def pause_monitor(db: Session, monitor: Monitor) -> Monitor:
    monitor.status = "paused"
    db.commit()
    db.refresh(monitor)

    from .scheduler import remove_monitor_job
    remove_monitor_job(str(monitor.id))
    return monitor


def resume_monitor(db: Session, monitor: Monitor) -> Monitor:
    monitor.status = "active"
    db.commit()
    db.refresh(monitor)

    if monitor.schedule_cron:
        from .scheduler import add_monitor_job
        add_monitor_job(str(monitor.id), monitor.schedule_cron, monitor.timezone)
    return monitor


# ── Check execution ─────────────────────────────────────────────────

async def execute_check(monitor_id: str, db: Session | None = None) -> dict[str, Any]:
    """Run a single check for a monitor: fetch data, detect changes, create alerts."""
    from ..database import SessionLocal

    own_session = db is None
    if own_session:
        db = SessionLocal()

    monitor_run = None
    try:
        monitor = db.query(Monitor).filter(Monitor.id == monitor_id).first()
        if not monitor:
            logger.warning("Monitor %s not found", monitor_id)
            return {"error": "not_found"}

        if monitor.status != "active":
            return {"skipped": "not_active"}

        # Create a MonitorRun record to track this check execution
        import time as time_mod
        check_start = time_mod.time()
        monitor_run = MonitorRun(
            monitor_id=monitor.id,
            project_id=monitor.project_id,
            status=RunStatus.created,
        )
        db.add(monitor_run)
        db.flush()

        # Transition: created -> queued -> running
        _transition_monitor_run(monitor_run, RunStatus.queued, "Check queued")
        _transition_monitor_run(monitor_run, RunStatus.running, "Check started")
        monitor_run.started_at = datetime.now(timezone.utc)
        db.flush()

        # Emit check start event
        await event_bus.broadcast(Event(
            event_type=EventType.monitor_triggered,
            data={"monitor_id": str(monitor.id), "monitor_name": monitor.name, "action": "check_start"},
            user_id=str(monitor.user_id),
            project_id=str(monitor.project_id) if monitor.project_id else None,
        ))

        # Fetch new data based on monitor type with timeout handling
        try:
            new_data = await asyncio.wait_for(
                _fetch_check_data(monitor),
                timeout=60.0,  # 60-second hard timeout for the fetch
            )
        except asyncio.TimeoutError:
            error_msg = f"Check timed out after 60s for monitor {monitor.name}"
            logger.warning(error_msg)
            _transition_monitor_run(monitor_run, RunStatus.failed, error_msg)
            monitor_run.failure_category = FailureCategory.timeout
            monitor_run.failure_message = error_msg
            monitor_run.completed_at = datetime.now(timezone.utc)
            monitor_run.duration_ms = int((time_mod.time() - check_start) * 1000)
            monitor_run.result = {"error": "timeout"}

            # Update monitor error tracking without creating a false-positive alert
            monitor.last_error = error_msg
            monitor.last_error_at = datetime.now(timezone.utc)
            monitor.total_checks = (monitor.total_checks or 0) + 1
            db.commit()
            return {"error": error_msg, "monitor_run_id": str(monitor_run.id)}

        # Check for fetch errors (connection errors, unreachable targets)
        if "error" in new_data and not new_data.get("status_code"):
            error_msg = new_data["error"]
            _transition_monitor_run(monitor_run, RunStatus.failed, error_msg)
            monitor_run.failure_category = FailureCategory.transient_connector
            monitor_run.failure_message = error_msg
            monitor_run.completed_at = datetime.now(timezone.utc)
            monitor_run.duration_ms = int((time_mod.time() - check_start) * 1000)
            monitor_run.result = new_data

            # Update monitor error tracking — do NOT create a false-positive alert
            monitor.last_error = error_msg
            monitor.last_error_at = datetime.now(timezone.utc)
            monitor.total_checks = (monitor.total_checks or 0) + 1
            db.commit()
            return {"error": error_msg, "monitor_run_id": str(monitor_run.id)}

        # Detect changes
        changes = _detect_changes(monitor, new_data)

        # Update monitor snapshot
        now = datetime.now(timezone.utc)
        monitor.last_check_at = now
        monitor.last_snapshot = new_data
        monitor.total_checks = (monitor.total_checks or 0) + 1

        # Clear error tracking on successful fetch
        monitor.last_error = None
        monitor.last_error_at = None

        alert = None
        if changes.changed:
            monitor.last_change_at = now

            # Alert deduplication: check cooldown using (monitor_id, alert_type)
            cooldown_seconds = (monitor.alert_config or {}).get(
                "cooldown_seconds", DEFAULT_ALERT_COOLDOWN_SECONDS,
            )
            alert_type = "change_detected"
            is_duplicate = _is_duplicate_alert(db, monitor.id, alert_type, cooldown_seconds)

            if is_duplicate:
                logger.info(
                    "Skipping duplicate alert for monitor %s (cooldown %ds, type=%s)",
                    monitor.id, cooldown_seconds, alert_type,
                )
            else:
                monitor.total_alerts = (monitor.total_alerts or 0) + 1
                alert = _create_alert(db, monitor, changes)

        # Complete the MonitorRun
        _transition_monitor_run(monitor_run, RunStatus.completed, changes.summary)
        monitor_run.completed_at = now
        monitor_run.duration_ms = int((time_mod.time() - check_start) * 1000)
        monitor_run.result = {
            "changed": changes.changed,
            "change_type": changes.change_type,
            "summary": changes.summary,
        }
        if alert:
            monitor_run.alert_id = alert.id

        db.commit()
        db.refresh(monitor)

        # Emit lifecycle event for the run
        await event_bus.broadcast(Event(
            event_type=EventType.run_state_changed,
            data={
                "run_type": "monitor",
                "run_id": str(monitor_run.id),
                "from_state": "running",
                "to_state": "completed",
                "reason": changes.summary,
            },
            user_id=str(monitor.user_id),
            project_id=str(monitor.project_id) if monitor.project_id else None,
        ))

        # Emit check done event
        await event_bus.broadcast(Event(
            event_type=EventType.monitor_triggered,
            data={
                "monitor_id": str(monitor.id),
                "monitor_name": monitor.name,
                "action": "check_done",
                "changed": changes.changed,
                "summary": changes.summary,
            },
            user_id=str(monitor.user_id),
            project_id=str(monitor.project_id) if monitor.project_id else None,
        ))

        # If alert was created, emit alert event, signal, and send notifications
        if alert:
            await event_bus.broadcast(Event(
                event_type=EventType.monitor_alert,
                data={
                    "alert_id": str(alert.id),
                    "monitor_name": monitor.name,
                    "title": alert.title,
                    "severity": str(alert.severity.value) if hasattr(alert.severity, 'value') else str(alert.severity),
                },
                user_id=str(monitor.user_id),
                project_id=str(monitor.project_id) if monitor.project_id else None,
            ))

            # Emit signal for the intelligence pipeline
            try:
                from .intelligence.signal_service import SignalService
                from ..models.signal import SignalSourceType, SignalType

                if monitor.project_id:
                    signal_svc = SignalService(db)
                    signal_type = (
                        SignalType.threshold_breached
                        if changes.change_type == "value"
                        else SignalType.change_detected
                    )
                    signal_svc.create_signal(
                        project_id=monitor.project_id,
                        user_id=monitor.user_id,
                        source_type=SignalSourceType.monitor,
                        signal_type=signal_type,
                        title=f"Monitor: {alert.title}",
                        content=alert.message,
                        structured_data=alert.data or {},
                        source_id=monitor_run.id if monitor_run else None,
                        confidence=None,
                    )
                    db.commit()
            except Exception:
                logger.debug("Signal emission failed for alert %s", alert.id)

            await _send_alert_notifications(alert, monitor)

        return {
            "monitor_id": str(monitor.id),
            "monitor_run_id": str(monitor_run.id),
            "changed": changes.changed,
            "summary": changes.summary,
            "alert_id": str(alert.id) if alert else None,
        }

    except Exception as exc:
        logger.error("Monitor check failed for %s: %s", monitor_id, exc, exc_info=True)
        try:
            if monitor_run is not None:
                monitor_run.status = RunStatus.failed
                monitor_run.failure_category = FailureCategory.internal
                monitor_run.failure_message = str(exc)
                monitor_run.completed_at = datetime.now(timezone.utc)
                transitions = list(monitor_run.state_transitions or [])
                transitions.append({
                    "from": "running",
                    "to": "failed",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "reason": str(exc),
                })
                monitor_run.state_transitions = transitions
                db.commit()
        except Exception:
            db.rollback()
        return {"error": str(exc)}
    finally:
        if own_session:
            db.close()


# ── Data fetching per monitor type ─────────────────────────────────

async def _fetch_check_data(monitor: Monitor) -> dict[str, Any]:
    """Fetch fresh data based on monitor type and check_config."""
    config = monitor.check_config or {}
    monitor_type = monitor.monitor_type

    if monitor_type in ("web_content", "competitor_tracker"):
        return await _fetch_web_content(config)
    elif monitor_type == "api_data":
        return await _fetch_api_data(config)
    elif monitor_type in ("price_tracker", "listing_watcher"):
        return await _fetch_web_content(config)
    elif monitor_type == "custom":
        return await _fetch_web_content(config)
    else:
        return {"error": f"Unknown monitor type: {monitor_type}"}


async def _fetch_web_content(config: dict) -> dict[str, Any]:
    """Fetch web page content."""
    url = config.get("url", "")
    if not url:
        return {"error": "No URL configured"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, follow_redirects=True)
            return {
                "status_code": resp.status_code,
                "content": resp.text[:50000],
                "url": str(resp.url),
            }
    except Exception as exc:
        return {"error": str(exc)}


async def _fetch_api_data(config: dict) -> dict[str, Any]:
    """Fetch data from an API endpoint."""
    url = config.get("url", "")
    method = config.get("method", "GET").upper()
    headers = config.get("headers", {})

    if not url:
        return {"error": "No URL configured"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(method, url, headers=headers)
            try:
                data = resp.json()
            except Exception:
                data = resp.text[:50000]
            return {"status_code": resp.status_code, "data": data}
    except Exception as exc:
        return {"error": str(exc)}


# ── Change detection ────────────────────────────────────────────────

def _detect_changes(monitor: Monitor, new_data: dict[str, Any]) -> ChangeResult:
    """Compare new_data to monitor's last_snapshot."""
    old = monitor.last_snapshot
    if old is None:
        return ChangeResult(
            changed=False,
            change_type="initial",
            summary="Initial snapshot captured",
            details={},
        )

    config = monitor.check_config or {}
    monitor_type = monitor.monitor_type

    if monitor_type in ("web_content", "competitor_tracker", "custom"):
        return detect_text_change(
            old.get("content", ""),
            new_data.get("content", ""),
        )
    elif monitor_type == "api_data":
        # Compare JSON data
        old_data = old.get("data")
        new_d = new_data.get("data")
        if isinstance(old_data, list) and isinstance(new_d, list):
            key = config.get("list_key", "id")
            new_items = detect_new_items(old_data, new_d, key)
            if new_items.changed:
                return new_items
            return detect_removed_items(old_data, new_d, key)
        return detect_text_change(str(old_data), str(new_d))
    elif monitor_type == "price_tracker":
        field = config.get("value_field", "price")
        threshold = config.get("threshold", 0)
        old_val = _extract_value(old, field)
        new_val = _extract_value(new_data, field)
        return detect_value_change(old_val, new_val, threshold)
    elif monitor_type == "listing_watcher":
        key = config.get("list_key", "id")
        old_list = old.get("data", []) if isinstance(old.get("data"), list) else []
        new_list = new_data.get("data", []) if isinstance(new_data.get("data"), list) else []
        return detect_new_items(old_list, new_list, key)
    else:
        return detect_text_change(str(old), str(new_data))


def _extract_value(data: dict, field: str) -> float | None:
    """Extract a numeric value from nested data using dot notation."""
    parts = field.split(".")
    current: Any = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    try:
        return float(current)
    except (TypeError, ValueError):
        return None


# ── Alert deduplication ────────────────────────────────────────────

def _is_duplicate_alert(
    db: Session,
    monitor_id: Any,
    alert_type: str,
    cooldown_seconds: int,
) -> bool:
    """Check if an alert with the same monitor_id and alert_type was created recently.

    Uses (monitor_id, alert_type) instead of dynamic title for stable dedup keys.
    Returns True if a matching alert exists within the cooldown window.
    """
    if cooldown_seconds <= 0:
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
    existing = (
        db.query(Alert)
        .filter(
            Alert.monitor_id == monitor_id,
            Alert.alert_type == alert_type,
            Alert.created_at >= cutoff,
        )
        .first()
    )
    return existing is not None


# ── Alert creation ──────────────────────────────────────────────────

def _create_alert(db: Session, monitor: Monitor, changes: ChangeResult) -> Alert:
    """Create an Alert record from a detected change."""
    severity_map = {
        "text": "info",
        "value": "warning",
        "new_items": "info",
        "removed_items": "warning",
    }
    severity = severity_map.get(changes.change_type, "info")

    alert = Alert(
        monitor_id=monitor.id,
        project_id=monitor.project_id,
        alert_type="change_detected",
        title=f"{monitor.name}: {changes.summary}",
        message=changes.summary,
        severity=severity,
        data=changes.details,
        delivered_channels=[],
    )
    db.add(alert)
    db.flush()
    return alert


# ── Alert notification delivery ─────────────────────────────────────

async def _send_alert_notifications(alert: Alert, monitor: Monitor) -> None:
    """Deliver alert via configured channels (email + dashboard)."""
    from ..database import SessionLocal

    channels = (monitor.alert_config or {}).get("channels", ["dashboard"])
    delivered: list[str] = []

    # Dashboard push is handled by the event emission above
    if "dashboard" in channels:
        delivered.append("dashboard")

    # Email via Resend
    if "email" in channels:
        try:
            await _send_alert_email(alert, monitor)
            delivered.append("email")
        except Exception as exc:
            logger.error("Failed to send alert email: %s", exc)

    # Update delivered channels
    db = SessionLocal()
    try:
        db_alert = db.query(Alert).filter(Alert.id == alert.id).first()
        if db_alert:
            db_alert.delivered_channels = delivered
            db.commit()
    finally:
        db.close()


async def _send_alert_email(alert: Alert, monitor: Monitor) -> None:
    """Send alert email via Resend API."""
    from ..config import settings

    if not settings.resend_api_key:
        logger.warning("No Resend API key configured, skipping email alert")
        return

    recipients = (monitor.alert_config or {}).get("recipients", [])
    if not recipients:
        return

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.resend_from_email,
                "to": recipients,
                "subject": f"[Agentary Alert] {alert.title}",
                "html": (
                    f"<h2>{alert.title}</h2>"
                    f"<p><strong>Monitor:</strong> {monitor.name}</p>"
                    f"<p><strong>Severity:</strong> {alert.severity}</p>"
                    f"<p>{alert.message}</p>"
                ),
            },
        )
