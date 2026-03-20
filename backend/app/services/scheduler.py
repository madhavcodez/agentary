from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from ..database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _get_active_user_ids() -> list:
    """Fetch all active user IDs from the database."""
    from ..models.user import User

    session = SessionLocal()
    try:
        return [
            row.id
            for row in session.query(User.id).filter(User.is_active == True).all()
        ]
    finally:
        session.close()


def _run_ingest():
    from .ingest.runner import run_all_connectors

    user_ids = _get_active_user_ids()
    for user_id in user_ids:
        session = SessionLocal()
        try:
            count = asyncio.run(run_all_connectors(session, user_id=user_id))
            logger.info(
                "Scheduled ingest completed for user %s: %d new opportunities",
                user_id, count,
            )
        except Exception as e:
            logger.error("Scheduled ingest failed for user %s: %s", user_id, e)
        finally:
            session.close()


def _run_scoring():
    from .match_engine import score_all_matches

    user_ids = _get_active_user_ids()
    for user_id in user_ids:
        session = SessionLocal()
        try:
            result = asyncio.run(score_all_matches(session, user_id=user_id))
            logger.info(
                "Scheduled scoring completed for user %s: %s", user_id, result,
            )
        except Exception as e:
            logger.error("Scheduled scoring failed for user %s: %s", user_id, e)
        finally:
            session.close()


def start_scheduler():
    scheduler.add_job(_run_ingest, "interval", hours=6, id="ingest_job", replace_existing=True)
    scheduler.add_job(_run_scoring, "interval", hours=24, id="scoring_job", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started: ingest every 6h, scoring every 24h")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
