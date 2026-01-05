"""
Privacy Settings Repository for Law 25 Compliance.

Handles database operations for user privacy settings and profile visibility.
"""

from sqlalchemy.orm import Session

from repositories import db_models
from repositories.base import BaseRepository


class PrivacyRepository(BaseRepository[db_models.User]):
    """Repository for privacy-related user data access."""

    def __init__(self, db: Session):
        """Initialize repository."""
        super().__init__(db_models.User, db)

    def get_user_approved_idea_count(self, user_id: int) -> int:
        """
        Get count of user's approved ideas.

        Args:
            user_id: User ID

        Returns:
            Count of approved, non-deleted ideas
        """
        return (
            self.db.query(db_models.Idea)
            .filter(
                db_models.Idea.user_id == user_id,
                db_models.Idea.deleted_at.is_(None),
                db_models.Idea.status == db_models.IdeaStatus.APPROVED,
            )
            .count()
        )

    def get_user_comment_count(self, user_id: int) -> int:
        """
        Get count of user's non-deleted comments.

        Args:
            user_id: User ID

        Returns:
            Count of non-deleted comments
        """
        return (
            self.db.query(db_models.Comment)
            .filter(
                db_models.Comment.user_id == user_id,
                db_models.Comment.deleted_at.is_(None),
            )
            .count()
        )
