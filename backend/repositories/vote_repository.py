"""
Vote repository for database operations.
"""

from typing import Optional, List
from sqlalchemy.orm import Session
import repositories.db_models as db_models
from .base import BaseRepository


class VoteRepository(BaseRepository[db_models.Vote]):
    """Repository for Vote entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize vote repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.Vote, db)

    def get_by_idea_and_user(
        self, idea_id: int, user_id: int
    ) -> Optional[db_models.Vote]:
        """
        Get vote by idea and user.

        Args:
            idea_id: Idea ID
            user_id: User ID

        Returns:
            Vote if found, None otherwise
        """
        return (
            self.db.query(db_models.Vote)
            .filter(
                db_models.Vote.idea_id == idea_id, db_models.Vote.user_id == user_id
            )
            .first()
        )

    def get_votes_for_idea(
        self, idea_id: int, vote_type: Optional[db_models.VoteType] = None
    ) -> List[db_models.Vote]:
        """
        Get all votes for an idea.

        Args:
            idea_id: Idea ID
            vote_type: Optional filter by vote type

        Returns:
            List of votes
        """
        query = self.db.query(db_models.Vote).filter(db_models.Vote.idea_id == idea_id)
        if vote_type:
            query = query.filter(db_models.Vote.vote_type == vote_type)
        return query.all()

    def get_votes_by_user(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> List[db_models.Vote]:
        """
        Get all votes by a user.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of votes
        """
        return (
            self.db.query(db_models.Vote)
            .filter(db_models.Vote.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def delete_by_idea_and_user(self, idea_id: int, user_id: int) -> bool:
        """
        Delete vote by idea and user.

        Args:
            idea_id: Idea ID
            user_id: User ID

        Returns:
            True if deleted, False if not found
        """
        vote = self.get_by_idea_and_user(idea_id, user_id)
        if not vote:
            return False

        self.db.delete(vote)
        self.db.commit()
        return True

    def delete_by_user_id(self, user_id: int) -> int:
        """
        Delete all votes by a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        count = (
            self.db.query(db_models.Vote)
            .filter(db_models.Vote.user_id == user_id)
            .delete()
        )
        return count

    def delete_by_idea_id(self, idea_id: int) -> int:
        """
        Delete all votes for an idea.

        Args:
            idea_id: Idea ID

        Returns:
            Number of deleted records
        """
        count = (
            self.db.query(db_models.Vote)
            .filter(db_models.Vote.idea_id == idea_id)
            .delete()
        )
        return count

    def get_vote_counts_batch(self, idea_ids: list[int]) -> dict[int, dict[str, int]]:
        """
        Get vote counts for multiple ideas in a single query.

        Args:
            idea_ids: List of idea IDs

        Returns:
            Dict mapping idea_id to {upvotes, downvotes, score}
        """
        from sqlalchemy import case, func

        if not idea_ids:
            return {}

        vote_counts = (
            self.db.query(
                db_models.Vote.idea_id,
                func.count(
                    case((db_models.Vote.vote_type == db_models.VoteType.UPVOTE, 1))
                ).label("upvotes"),
                func.count(
                    case((db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE, 1))
                ).label("downvotes"),
            )
            .filter(db_models.Vote.idea_id.in_(idea_ids))
            .group_by(db_models.Vote.idea_id)
            .all()
        )

        result: dict[int, dict[str, int]] = {}
        for idea_id, upvotes, downvotes in vote_counts:
            result[idea_id] = {
                "upvotes": upvotes or 0,
                "downvotes": downvotes or 0,
                "score": (upvotes or 0) - (downvotes or 0),
            }

        # Fill in zeros for ideas with no votes
        for idea_id in idea_ids:
            if idea_id not in result:
                result[idea_id] = {"upvotes": 0, "downvotes": 0, "score": 0}

        return result
