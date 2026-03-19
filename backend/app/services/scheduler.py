from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from ..database import SessionLocal

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


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


def start_scheduler():
    scheduler.add_job(_run_ingest, "interval", hours=6, id="ingest_job", replace_existing=True)
    scheduler.add_job(_run_scoring, "interval", hours=24, id="scoring_job", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started: ingest every 6h, scoring every 24h")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
