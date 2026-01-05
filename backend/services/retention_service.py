"""
Data Retention Service for Law 25 Compliance.

Implements automated cleanup of expired data according to retention policies.
Article 11 (Destruction), Article 12 (Retention Schedules), Article 13 (Anonymization).
"""

from datetime import datetime, timedelta, timezone
from typing import Tuple

from loguru import logger
from sqlalchemy.orm import Session

import repositories.db_models as db_models
from models.config import settings
from repositories.consent_log_repository import ConsentLogRepository
from repositories.retention_repository import RetentionRepository


class RetentionService:
    """
    Service for enforcing data retention policies.

    Should be run via scheduled task (background scheduler).
    """

    @staticmethod
    def run_all_cleanup_jobs(db: Session) -> dict:
        """
        Run all retention cleanup jobs.

        Returns:
            Summary of cleanup actions taken
        """
        logger.info("Starting retention cleanup jobs")

        results = {
            "soft_deleted_content": RetentionService.cleanup_soft_deleted_content(db),
            "expired_login_codes": RetentionService.cleanup_expired_login_codes(db),
            "inactive_accounts": RetentionService.process_inactive_accounts(db),
        }

        logger.info(f"Retention cleanup complete: {results}")
        return results

    @staticmethod
    def cleanup_soft_deleted_content(db: Session) -> Tuple[int, int]:
        """
        Permanently delete soft-deleted content past retention period.

        Returns:
            Tuple of (deleted_ideas_count, deleted_comments_count)
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=settings.SOFT_DELETE_RETENTION_DAYS
        )

        retention_repo = RetentionRepository(db)

        # Get IDs of ideas to delete for cascade cleanup
        idea_ids = retention_repo.get_soft_deleted_idea_ids(cutoff_date)

        # Delete related records first (foreign key constraints)
        if idea_ids:
            retention_repo.delete_idea_tags_by_idea_ids(idea_ids)
            retention_repo.delete_votes_by_idea_ids(idea_ids)
            retention_repo.delete_comments_by_idea_ids(idea_ids)

        # Delete the ideas
        deleted_ideas = retention_repo.delete_soft_deleted_ideas(cutoff_date)

        # Delete orphaned comments (soft-deleted past retention)
        deleted_comments = retention_repo.delete_soft_deleted_comments(cutoff_date)

        retention_repo.commit()

        logger.info(
            f"Cleaned up soft-deleted content: {deleted_ideas} ideas, "
            f"{deleted_comments} comments"
        )

        return (deleted_ideas, deleted_comments)

    @staticmethod
    def cleanup_expired_login_codes(db: Session) -> int:
        """
        Delete expired email login codes past retention period.

        Returns:
            Number of deleted codes
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=settings.EXPIRED_LOGIN_CODE_RETENTION_DAYS
        )

        retention_repo = RetentionRepository(db)
        deleted_count = retention_repo.delete_expired_login_codes(cutoff_date)
        retention_repo.commit()

        logger.info(f"Cleaned up {deleted_count} expired login codes")
        return deleted_count

    @staticmethod
    def _warn_inactive_users(
        retention_repo: RetentionRepository,
        inactivity_threshold: datetime,
        now: datetime,
        grace_period: timedelta,
    ) -> int:
        """Send warnings to inactive users and schedule anonymization."""
        users_to_warn = retention_repo.get_users_to_warn_for_inactivity(
            inactivity_threshold
        )

        for user in users_to_warn:
            RetentionService._send_inactivity_warning(user)
            user.inactivity_warning_sent_at = now
            user.scheduled_anonymization_at = now + grace_period

        return len(users_to_warn)

    @staticmethod
    def _anonymize_inactive_users(
        retention_repo: RetentionRepository,
        consent_repo: ConsentLogRepository,
        now: datetime,
        db: Session,
    ) -> int:
        """Anonymize users past grace period."""
        from repositories.account_deletion_repository import AccountDeletionRepository
        from services.account_deletion_service import AccountDeletionService

        deletion_repo = AccountDeletionRepository(db)
        users_to_anonymize = retention_repo.get_users_past_grace_period(now)

        for user in users_to_anonymize:
            AccountDeletionService._anonymize_user_profile(user)
            AccountDeletionService._delete_sensitive_data(deletion_repo, user.id)
            consent_repo.create_consent_log(
                user_id=user.id, consent_type="account", action="anonymized_inactive"
            )
            logger.info(f"Anonymized inactive account: user_id={user.id}")

        return len(users_to_anonymize)

    @staticmethod
    def process_inactive_accounts(db: Session) -> dict:
        """Process inactive accounts: warn inactive users, anonymize past grace."""
        now = datetime.now(timezone.utc)
        inactivity_threshold = now - timedelta(
            days=settings.INACTIVE_ACCOUNT_RETENTION_YEARS * 365
        )
        grace_period = timedelta(days=settings.INACTIVE_ACCOUNT_GRACE_PERIOD_DAYS)

        retention_repo = RetentionRepository(db)
        consent_repo = ConsentLogRepository(db)

        warnings_sent = RetentionService._warn_inactive_users(
            retention_repo, inactivity_threshold, now, grace_period
        )
        accounts_anonymized = RetentionService._anonymize_inactive_users(
            retention_repo, consent_repo, now, db
        )

        retention_repo.flush()

        logger.info(
            f"Processed inactive accounts: {warnings_sent} warned, "
            f"{accounts_anonymized} anonymized"
        )

        return {
            "warnings_sent": warnings_sent,
            "accounts_anonymized": accounts_anonymized,
        }

    @staticmethod
    def _send_inactivity_warning(user: db_models.User) -> None:
        """
        Send inactivity warning email to user.

        TODO: Integrate with email service when available.
        """
        logger.info(f"Would send inactivity warning to user {user.id} at {user.email}")

    @staticmethod
    def cleanup_old_consent_logs(db: Session) -> int:
        """
        Clean up consent logs past retention period.

        Note: Only delete logs older than CONSENT_LOG_RETENTION_YEARS
        for users that have been deleted/anonymized.

        Returns:
            Number of deleted logs
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(
            days=settings.CONSENT_LOG_RETENTION_YEARS * 365
        )

        consent_repo = ConsentLogRepository(db)
        deleted_count = consent_repo.delete_old_logs_for_deleted_users(cutoff_date)

        logger.info(f"Cleaned up {deleted_count} old consent logs")
        return deleted_count


class RetentionMetrics:
    """
    Metrics and reporting for retention compliance.
    """

    @staticmethod
    def get_retention_status(db: Session) -> dict:
        """
        Get current retention status for monitoring dashboard.
        """
        now = datetime.now(timezone.utc)

        soft_delete_cutoff = now - timedelta(days=settings.SOFT_DELETE_RETENTION_DAYS)
        inactivity_cutoff = now - timedelta(
            days=settings.INACTIVE_ACCOUNT_RETENTION_YEARS * 365
        )

        retention_repo = RetentionRepository(db)

        return {
            "soft_deleted_ideas_pending": retention_repo.count_soft_deleted_ideas_pending(
                soft_delete_cutoff
            ),
            "soft_deleted_ideas_ready_for_deletion": retention_repo.count_soft_deleted_ideas_ready(
                soft_delete_cutoff
            ),
            "soft_deleted_comments_pending": retention_repo.count_soft_deleted_comments_pending(
                soft_delete_cutoff
            ),
            "soft_deleted_comments_ready_for_deletion": retention_repo.count_soft_deleted_comments_ready(
                soft_delete_cutoff
            ),
            "inactive_users_pending_warning": retention_repo.count_inactive_users_pending_warning(
                inactivity_cutoff
            ),
            "users_pending_anonymization": retention_repo.count_users_pending_anonymization(
                now
            ),
            "expired_login_codes": retention_repo.count_expired_login_codes(now),
            "retention_config": {
                "soft_delete_retention_days": settings.SOFT_DELETE_RETENTION_DAYS,
                "inactive_account_retention_years": settings.INACTIVE_ACCOUNT_RETENTION_YEARS,
                "inactive_account_grace_period_days": settings.INACTIVE_ACCOUNT_GRACE_PERIOD_DAYS,
                "expired_login_code_retention_days": settings.EXPIRED_LOGIN_CODE_RETENTION_DAYS,
                "consent_log_retention_years": settings.CONSENT_LOG_RETENTION_YEARS,
            },
        }
