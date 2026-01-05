"""
Retention Repository for Law 25 Compliance.

Provides database operations for data retention cleanup.
"""

from datetime import datetime

from sqlalchemy.orm import Session

import repositories.db_models as db_models

from .base import BaseRepository


class RetentionRepository(BaseRepository[db_models.User]):
    """Repository for retention cleanup operations."""

    def __init__(self, db: Session):
        """
        Initialize retention repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.User, db)

    def get_soft_deleted_idea_ids(self, cutoff_date: datetime) -> list[int]:
        """
        Get IDs of ideas soft-deleted before cutoff date.

        Args:
            cutoff_date: Cutoff date for deletion

        Returns:
            List of idea IDs
        """
        results = (
            self.db.query(db_models.Idea.id)
            .filter(
                db_models.Idea.deleted_at.isnot(None),
                db_models.Idea.deleted_at < cutoff_date,
            )
            .all()
        )
        return [r[0] for r in results]

    def delete_idea_tags_by_idea_ids(self, idea_ids: list[int]) -> int:
        """
        Delete idea tags for given idea IDs.

        Args:
            idea_ids: List of idea IDs

        Returns:
            Number of deleted records
        """
        if not idea_ids:
            return 0
        return (
            self.db.query(db_models.IdeaTag)
            .filter(db_models.IdeaTag.idea_id.in_(idea_ids))
            .delete(synchronize_session=False)
        )

    def delete_votes_by_idea_ids(self, idea_ids: list[int]) -> int:
        """
        Delete votes for given idea IDs.

        Args:
            idea_ids: List of idea IDs

        Returns:
            Number of deleted records
        """
        if not idea_ids:
            return 0
        return (
            self.db.query(db_models.Vote)
            .filter(db_models.Vote.idea_id.in_(idea_ids))
            .delete(synchronize_session=False)
        )

    def delete_comments_by_idea_ids(self, idea_ids: list[int]) -> int:
        """
        Delete comments for given idea IDs.

        Args:
            idea_ids: List of idea IDs

        Returns:
            Number of deleted records
        """
        if not idea_ids:
            return 0
        return (
            self.db.query(db_models.Comment)
            .filter(db_models.Comment.idea_id.in_(idea_ids))
            .delete(synchronize_session=False)
        )

    def delete_soft_deleted_ideas(self, cutoff_date: datetime) -> int:
        """
        Permanently delete soft-deleted ideas past retention period.

        Args:
            cutoff_date: Delete ideas deleted before this date

        Returns:
            Number of deleted ideas
        """
        return (
            self.db.query(db_models.Idea)
            .filter(
                db_models.Idea.deleted_at.isnot(None),
                db_models.Idea.deleted_at < cutoff_date,
            )
            .delete(synchronize_session=False)
        )

    def delete_soft_deleted_comments(self, cutoff_date: datetime) -> int:
        """
        Permanently delete soft-deleted comments past retention period.

        Args:
            cutoff_date: Delete comments deleted before this date

        Returns:
            Number of deleted comments
        """
        return (
            self.db.query(db_models.Comment)
            .filter(
                db_models.Comment.deleted_at.isnot(None),
                db_models.Comment.deleted_at < cutoff_date,
            )
            .delete(synchronize_session=False)
        )

    def delete_expired_login_codes(self, cutoff_date: datetime) -> int:
        """
        Delete email login codes expired before cutoff date.

        Args:
            cutoff_date: Delete codes expired before this date

        Returns:
            Number of deleted codes
        """
        return (
            self.db.query(db_models.EmailLoginCode)
            .filter(db_models.EmailLoginCode.expires_at < cutoff_date)
            .delete(synchronize_session=False)
        )

    def get_users_to_warn_for_inactivity(
        self, inactivity_threshold: datetime
    ) -> list[db_models.User]:
        """
        Get users who are inactive but haven't been warned yet.

        Args:
            inactivity_threshold: Users inactive before this date

        Returns:
            List of users to warn
        """
        return (
            self.db.query(db_models.User)
            .filter(
                db_models.User.is_active == True,  # noqa: E712
                db_models.User.last_activity_at.isnot(None),
                db_models.User.last_activity_at < inactivity_threshold,
                db_models.User.inactivity_warning_sent_at.is_(None),
                db_models.User.scheduled_anonymization_at.is_(None),
            )
            .all()
        )

    def get_users_past_grace_period(self, now: datetime) -> list[db_models.User]:
        """
        Get users who were warned and are past their grace period.

        Args:
            now: Current datetime

        Returns:
            List of users to anonymize
        """
        return (
            self.db.query(db_models.User)
            .filter(
                db_models.User.is_active == True,  # noqa: E712
                db_models.User.scheduled_anonymization_at.isnot(None),
                db_models.User.scheduled_anonymization_at < now,
            )
            .all()
        )

    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()

    def flush(self) -> None:
        """Flush pending changes without committing."""
        self.db.flush()

    def count_soft_deleted_ideas_pending(self, cutoff_date: datetime) -> int:
        """Count soft-deleted ideas not yet past retention."""
        return (
            self.db.query(db_models.Idea)
            .filter(
                db_models.Idea.deleted_at.isnot(None),
                db_models.Idea.deleted_at >= cutoff_date,
            )
            .count()
        )

    def count_soft_deleted_ideas_ready(self, cutoff_date: datetime) -> int:
        """Count soft-deleted ideas ready for permanent deletion."""
        return (
            self.db.query(db_models.Idea)
            .filter(
                db_models.Idea.deleted_at.isnot(None),
                db_models.Idea.deleted_at < cutoff_date,
            )
            .count()
        )

    def count_soft_deleted_comments_pending(self, cutoff_date: datetime) -> int:
        """Count soft-deleted comments not yet past retention."""
        return (
            self.db.query(db_models.Comment)
            .filter(
                db_models.Comment.deleted_at.isnot(None),
                db_models.Comment.deleted_at >= cutoff_date,
            )
            .count()
        )

    def count_soft_deleted_comments_ready(self, cutoff_date: datetime) -> int:
        """Count soft-deleted comments ready for permanent deletion."""
        return (
            self.db.query(db_models.Comment)
            .filter(
                db_models.Comment.deleted_at.isnot(None),
                db_models.Comment.deleted_at < cutoff_date,
            )
            .count()
        )

    def count_inactive_users_pending_warning(
        self, inactivity_threshold: datetime
    ) -> int:
        """Count inactive users who haven't been warned."""
        return (
            self.db.query(db_models.User)
            .filter(
                db_models.User.is_active == True,  # noqa: E712
                db_models.User.last_activity_at.isnot(None),
                db_models.User.last_activity_at < inactivity_threshold,
                db_models.User.inactivity_warning_sent_at.is_(None),
            )
            .count()
        )

    def count_users_pending_anonymization(self, now: datetime) -> int:
        """Count users past grace period awaiting anonymization."""
        return (
            self.db.query(db_models.User)
            .filter(
                db_models.User.scheduled_anonymization_at.isnot(None),
                db_models.User.scheduled_anonymization_at < now,
            )
            .count()
        )

    def count_expired_login_codes(self, now: datetime) -> int:
        """Count expired login codes."""
        return (
            self.db.query(db_models.EmailLoginCode)
            .filter(db_models.EmailLoginCode.expires_at < now)
            .count()
        )
