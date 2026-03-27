"""One-time migration tasks."""
from __future__ import annotations

import logging

from ..celery_app import celery_app
from ..database import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, soft_time_limit=3600)
def migrate_findings_to_observations(self, batch_size: int = 100):
    """Migrate existing findings to observations. Idempotent -- skips already-migrated."""
    db = SessionLocal()
    try:
        from ..models.finding import Finding
        from ..services.intelligence.observation_service import ObservationService

        obs_svc = ObservationService(db)
        total = 0

        while True:
            findings = (
                db.query(Finding)
                .filter(Finding.observation_id.is_(None))
                .limit(batch_size)
                .all()
            )
            if not findings:
                break

            for f in findings:
                try:
                    obs_svc.create_from_finding(f)
                    total += 1
                except Exception as e:
                    logger.warning("Failed to migrate finding %s: %s", f.id, e)

            db.commit()
            logger.info("Migrated %d findings so far", total)

        return {"status": "completed", "total_migrated": total}
    finally:
        db.close()
