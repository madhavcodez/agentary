"""Manage shareable report links."""

import logging
import secrets
from uuid import UUID

from sqlalchemy.orm import Session

from ...config import settings
from ...models.report import Report

logger = logging.getLogger(__name__)


class ShareService:
    """Manage shareable report links.

    Provides methods to create, retrieve, and revoke shareable links for
    reports. Share tokens are generated with ``secrets.token_urlsafe`` and
    stored directly on the ``Report`` model.
    """

    def create_share_link(
        self,
        report_id: UUID,
        user_id: UUID,
        db: Session,
    ) -> dict:
        """Generate a unique share token and enable sharing.

        Steps:
            1. Verify the report exists and belongs to the requesting user.
            2. Generate a cryptographically secure token.
            3. Persist ``share_token`` and set ``share_enabled = True``.
            4. Return the public URL and token.

        Args:
            report_id: The report to share.
            user_id:   The user requesting the share link (must own the report).
            db:        Active SQLAlchemy session.

        Returns:
            ``{"url": "<base_url>/shared/reports/<token>", "token": "<token>"}``

        Raises:
            ValueError: If the report does not exist or does not belong to the user.
        """
        report = db.query(Report).filter(Report.id == report_id).first()

        if report is None:
            logger.warning(
                "Share link requested for non-existent report %s by user %s",
                report_id,
                user_id,
            )
            raise ValueError(f"Report {report_id} not found.")

        if report.user_id != user_id:
            logger.warning(
                "User %s attempted to share report %s owned by %s",
                user_id,
                report_id,
                report.user_id,
            )
            raise ValueError("You do not have permission to share this report.")

        # If the report already has an active share link, return it instead of
        # generating a new one, to keep URLs stable.
        if report.share_enabled and report.share_token:
            token = report.share_token
            logger.info(
                "Returning existing share link for report %s", report_id
            )
            return {
                "url": f"{settings.base_url}/shared/reports/{token}",
                "token": token,
            }

        token = secrets.token_urlsafe(32)
        report.share_token = token
        report.share_enabled = True

        db.commit()
        db.refresh(report)

        logger.info(
            "Created share link for report %s (user %s)", report_id, user_id
        )

        return {
            "url": f"{settings.base_url}/shared/reports/{token}",
            "token": token,
        }

    def get_shared_report(
        self,
        share_token: str,
        db: Session,
    ) -> Report | None:
        """Fetch a report by its share token. No authentication required.

        Returns the ``Report`` if the token matches an existing report that
        has sharing enabled. Returns ``None`` if the token is invalid, the
        report does not exist, or sharing has been revoked.

        Args:
            share_token: The token from the shareable URL.
            db:          Active SQLAlchemy session.
        """
        if not share_token:
            return None

        report = (
            db.query(Report)
            .filter(
                Report.share_token == share_token,
                Report.share_enabled.is_(True),
            )
            .first()
        )

        if report is None:
            logger.debug(
                "Shared report lookup failed for token %.8s...", share_token
            )
            return None

        logger.info(
            "Shared report %s accessed via token %.8s...",
            report.id,
            share_token,
        )
        return report

    def revoke_share(
        self,
        report_id: UUID,
        user_id: UUID,
        db: Session,
    ) -> None:
        """Disable sharing and clear the share token.

        Args:
            report_id: The report whose sharing should be revoked.
            user_id:   The user requesting revocation (must own the report).
            db:        Active SQLAlchemy session.

        Raises:
            ValueError: If the report does not exist or does not belong to the user.
        """
        report = db.query(Report).filter(Report.id == report_id).first()

        if report is None:
            logger.warning(
                "Revoke requested for non-existent report %s by user %s",
                report_id,
                user_id,
            )
            raise ValueError(f"Report {report_id} not found.")

        if report.user_id != user_id:
            logger.warning(
                "User %s attempted to revoke share for report %s owned by %s",
                user_id,
                report_id,
                report.user_id,
            )
            raise ValueError("You do not have permission to modify this report.")

        report.share_enabled = False
        report.share_token = None

        db.commit()

        logger.info(
            "Revoked share link for report %s (user %s)", report_id, user_id
        )
