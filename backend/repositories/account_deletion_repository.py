"""
Account Deletion Repository for Law 25 Compliance.

Provides database operations for account deletion and anonymization.
"""

from datetime import datetime

from sqlalchemy.orm import Session

import repositories.db_models as db_models

from .base import BaseRepository


class AccountDeletionRepository(BaseRepository[db_models.User]):
    """Repository for account deletion operations."""

    def __init__(self, db: Session):
        """
        Initialize account deletion repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.User, db)

    def delete_totp_secrets(self, user_id: int) -> int:
        """
        Delete 2FA TOTP secrets for a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        return (
            self.db.query(db_models.UserTOTPSecret)
            .filter(db_models.UserTOTPSecret.user_id == user_id)
            .delete(synchronize_session=False)
        )

    def delete_backup_codes(self, user_id: int) -> int:
        """
        Delete backup codes for a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        return (
            self.db.query(db_models.UserBackupCode)
            .filter(db_models.UserBackupCode.user_id == user_id)
            .delete(synchronize_session=False)
        )

    def delete_email_login_codes(self, user_id: int) -> int:
        """
        Delete email login codes for a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        return (
            self.db.query(db_models.EmailLoginCode)
            .filter(db_models.EmailLoginCode.user_id == user_id)
            .delete(synchronize_session=False)
        )

    def delete_admin_roles(self, user_id: int) -> int:
        """
        Delete admin roles for a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        return (
            self.db.query(db_models.AdminRole)
            .filter(db_models.AdminRole.user_id == user_id)
            .delete(synchronize_session=False)
        )

    def get_vote_ids_by_user(self, user_id: int) -> list[int]:
        """
        Get all vote IDs for a user.

        Args:
            user_id: User ID

        Returns:
            List of vote IDs
        """
        results = (
            self.db.query(db_models.Vote.id)
            .filter(db_models.Vote.user_id == user_id)
            .all()
        )
        return [r[0] for r in results]

    def delete_vote_qualities_by_vote_ids(self, vote_ids: list[int]) -> int:
        """
        Delete vote qualities for given vote IDs.

        Args:
            vote_ids: List of vote IDs

        Returns:
            Number of deleted records
        """
        if not vote_ids:
            return 0
        return (
            self.db.query(db_models.VoteQuality)
            .filter(db_models.VoteQuality.vote_id.in_(vote_ids))
            .delete(synchronize_session=False)
        )

    def delete_votes_by_user(self, user_id: int) -> int:
        """
        Delete all votes for a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        return (
            self.db.query(db_models.Vote)
            .filter(db_models.Vote.user_id == user_id)
            .delete(synchronize_session=False)
        )

    def delete_comment_likes_by_user(self, user_id: int) -> int:
        """
        Delete comment likes by a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        return (
            self.db.query(db_models.CommentLike)
            .filter(db_models.CommentLike.user_id == user_id)
            .delete(synchronize_session=False)
        )

    def delete_content_flags_by_reporter(self, user_id: int) -> int:
        """
        Delete content flags submitted by a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        return (
            self.db.query(db_models.ContentFlag)
            .filter(db_models.ContentFlag.reporter_id == user_id)
            .delete(synchronize_session=False)
        )

    def get_idea_ids_by_user(self, user_id: int) -> list[int]:
        """
        Get all idea IDs for a user.

        Args:
            user_id: User ID

        Returns:
            List of idea IDs
        """
        results = (
            self.db.query(db_models.Idea.id)
            .filter(db_models.Idea.user_id == user_id)
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

    def soft_delete_comments_by_user(self, user_id: int, deleted_at: datetime) -> int:
        """
        Soft delete all comments by a user.

        Args:
            user_id: User ID
            deleted_at: Deletion timestamp

        Returns:
            Number of updated records
        """
        return (
            self.db.query(db_models.Comment)
            .filter(db_models.Comment.user_id == user_id)
            .update(
                {
                    "deleted_at": deleted_at,
                    "content": "[Comment deleted by user]",
                },
                synchronize_session=False,
            )
        )

    def soft_delete_ideas_by_user(self, user_id: int, deleted_at: datetime) -> int:
        """
        Soft delete all ideas by a user.

        Args:
            user_id: User ID
            deleted_at: Deletion timestamp

        Returns:
            Number of updated records
        """
        return (
            self.db.query(db_models.Idea)
            .filter(db_models.Idea.user_id == user_id)
            .update(
                {
                    "deleted_at": deleted_at,
                    "title": "[Idea deleted by user]",
                    "description": "[Content deleted by user]",
                },
                synchronize_session=False,
            )
        )

    def commit(self) -> None:
        """Commit the current transaction."""
        self.db.commit()
