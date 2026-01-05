"""
Data Export Repository for Law 25 Compliance.

Provides read-only access to user data for export functionality.
"""

from sqlalchemy import case, func
from sqlalchemy.orm import Session

import repositories.db_models as db_models

from .base import BaseRepository


class DataExportRepository(BaseRepository[db_models.User]):
    """Repository for user data export operations."""

    def __init__(self, db: Session):
        """
        Initialize data export repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.User, db)

    def get_user_ideas_for_export(self, user_id: int) -> list[db_models.Idea]:
        """
        Get all non-deleted ideas for a user.

        Args:
            user_id: User ID

        Returns:
            List of ideas
        """
        return (
            self.db.query(db_models.Idea)
            .filter(
                db_models.Idea.user_id == user_id,
                db_models.Idea.deleted_at.is_(None),
            )
            .all()
        )

    def get_idea_vote_counts(self, idea_ids: list[int]) -> dict[int, dict[str, int]]:
        """
        Get vote counts (upvotes/downvotes) for a list of ideas.

        Args:
            idea_ids: List of idea IDs

        Returns:
            Dict mapping idea_id to {upvotes, downvotes}
        """
        if not idea_ids:
            return {}

        counts = (
            self.db.query(
                db_models.Vote.idea_id,
                func.sum(
                    case(
                        (db_models.Vote.vote_type == db_models.VoteType.UPVOTE, 1),
                        else_=0,
                    )
                ).label("upvotes"),
                func.sum(
                    case(
                        (db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE, 1),
                        else_=0,
                    )
                ).label("downvotes"),
            )
            .filter(db_models.Vote.idea_id.in_(idea_ids))
            .group_by(db_models.Vote.idea_id)
            .all()
        )

        result: dict[int, dict[str, int]] = {}
        for count in counts:
            result[count.idea_id] = {
                "upvotes": count.upvotes or 0,
                "downvotes": count.downvotes or 0,
            }
        return result

    def get_user_comments_for_export(self, user_id: int) -> list[db_models.Comment]:
        """
        Get all non-deleted comments for a user.

        Args:
            user_id: User ID

        Returns:
            List of comments
        """
        return (
            self.db.query(db_models.Comment)
            .filter(
                db_models.Comment.user_id == user_id,
                db_models.Comment.deleted_at.is_(None),
            )
            .all()
        )

    def get_user_votes_for_export(self, user_id: int) -> list[db_models.Vote]:
        """
        Get all votes for a user.

        Args:
            user_id: User ID

        Returns:
            List of votes
        """
        return (
            self.db.query(db_models.Vote)
            .filter(db_models.Vote.user_id == user_id)
            .all()
        )

    def get_user_consent_logs(self, user_id: int) -> list[db_models.ConsentLog]:
        """
        Get consent history for a user, ordered by most recent first.

        Args:
            user_id: User ID

        Returns:
            List of consent logs
        """
        return (
            self.db.query(db_models.ConsentLog)
            .filter(db_models.ConsentLog.user_id == user_id)
            .order_by(db_models.ConsentLog.created_at.desc())
            .all()
        )
