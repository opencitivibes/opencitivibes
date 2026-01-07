"""
Vote repository for database operations.
"""

from typing import Optional, List

from sqlalchemy import case, func
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

    def get_trust_distribution_for_idea(self, idea_id: int) -> dict[str, int]:
        """
        Get trust score distribution of voters for an idea.

        Joins votes with users, groups by trust level buckets.

        Args:
            idea_id: Idea ID

        Returns:
            Dict with trust level counts: {excellent, good, average, below_average, low, total_votes}
        """
        # Only count upvotes for trust distribution
        result = (
            self.db.query(
                func.sum(case((db_models.User.trust_score > 80, 1), else_=0)).label(
                    "excellent"
                ),
                func.sum(
                    case(
                        (
                            (db_models.User.trust_score > 60)
                            & (db_models.User.trust_score <= 80),
                            1,
                        ),
                        else_=0,
                    )
                ).label("good"),
                func.sum(
                    case(
                        (
                            (db_models.User.trust_score > 40)
                            & (db_models.User.trust_score <= 60),
                            1,
                        ),
                        else_=0,
                    )
                ).label("average"),
                func.sum(
                    case(
                        (
                            (db_models.User.trust_score > 20)
                            & (db_models.User.trust_score <= 40),
                            1,
                        ),
                        else_=0,
                    )
                ).label("below_average"),
                func.sum(case((db_models.User.trust_score <= 20, 1), else_=0)).label(
                    "low"
                ),
                func.count(db_models.Vote.id).label("total_votes"),
            )
            .join(db_models.User, db_models.Vote.user_id == db_models.User.id)
            .filter(
                db_models.Vote.idea_id == idea_id,
                db_models.Vote.vote_type == db_models.VoteType.UPVOTE,
            )
            .first()
        )

        if not result or result.total_votes is None:
            return {
                "excellent": 0,
                "good": 0,
                "average": 0,
                "below_average": 0,
                "low": 0,
                "total_votes": 0,
            }

        return {
            "excellent": result.excellent or 0,
            "good": result.good or 0,
            "average": result.average or 0,
            "below_average": result.below_average or 0,
            "low": result.low or 0,
            "total_votes": result.total_votes or 0,
        }

    def get_trust_distribution_batch(
        self, idea_ids: list[int]
    ) -> dict[int, dict[str, int]]:
        """
        Get trust distribution for multiple ideas in a single query (N+1 prevention).

        Args:
            idea_ids: List of idea IDs

        Returns:
            Dict mapping idea_id to trust distribution
        """
        if not idea_ids:
            return {}

        result = (
            self.db.query(
                db_models.Vote.idea_id,
                func.sum(case((db_models.User.trust_score > 80, 1), else_=0)).label(
                    "excellent"
                ),
                func.sum(
                    case(
                        (
                            (db_models.User.trust_score > 60)
                            & (db_models.User.trust_score <= 80),
                            1,
                        ),
                        else_=0,
                    )
                ).label("good"),
                func.sum(
                    case(
                        (
                            (db_models.User.trust_score > 40)
                            & (db_models.User.trust_score <= 60),
                            1,
                        ),
                        else_=0,
                    )
                ).label("average"),
                func.sum(
                    case(
                        (
                            (db_models.User.trust_score > 20)
                            & (db_models.User.trust_score <= 40),
                            1,
                        ),
                        else_=0,
                    )
                ).label("below_average"),
                func.sum(case((db_models.User.trust_score <= 20, 1), else_=0)).label(
                    "low"
                ),
                func.count(db_models.Vote.id).label("total_votes"),
            )
            .join(db_models.User, db_models.Vote.user_id == db_models.User.id)
            .filter(
                db_models.Vote.idea_id.in_(idea_ids),
                db_models.Vote.vote_type == db_models.VoteType.UPVOTE,
            )
            .group_by(db_models.Vote.idea_id)
            .all()
        )

        # Build result dict
        distributions: dict[int, dict[str, int]] = {}
        for row in result:
            distributions[row.idea_id] = {
                "excellent": row.excellent or 0,
                "good": row.good or 0,
                "average": row.average or 0,
                "below_average": row.below_average or 0,
                "low": row.low or 0,
                "total_votes": row.total_votes or 0,
            }

        # Fill in zeros for ideas with no votes
        for idea_id in idea_ids:
            if idea_id not in distributions:
                distributions[idea_id] = {
                    "excellent": 0,
                    "good": 0,
                    "average": 0,
                    "below_average": 0,
                    "low": 0,
                    "total_votes": 0,
                }

        return distributions

    def get_stakeholder_distribution_for_idea(self, idea_id: int) -> dict[str, int]:
        """
        Get stakeholder type distribution for voters on an idea (future-proofing).

        Groups by Vote.stakeholder_type if populated.

        Args:
            idea_id: Idea ID

        Returns:
            Dict mapping stakeholder_type to count (e.g., {resident: 5, expert: 2})
        """
        # This is a placeholder for future stakeholder voting feature
        # For now, return empty dict since stakeholder_type isn't on Vote model
        return {}
