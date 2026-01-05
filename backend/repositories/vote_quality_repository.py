"""
Vote quality repository for database operations.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from repositories.base import BaseRepository
from repositories.db_models import Quality, Vote, VoteQuality, VoteType


class VoteQualityRepository(BaseRepository[VoteQuality]):
    """Repository for VoteQuality entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize vote quality repository.

        Args:
            db: Database session
        """
        super().__init__(VoteQuality, db)

    def get_by_vote_id(self, vote_id: int) -> list[VoteQuality]:
        """
        Get all vote qualities for a specific vote.

        Args:
            vote_id: Vote ID

        Returns:
            List of VoteQuality records
        """
        return self.db.query(VoteQuality).filter(VoteQuality.vote_id == vote_id).all()

    def get_quality_ids_by_vote(self, vote_id: int) -> list[int]:
        """
        Get list of quality IDs for a vote.

        Args:
            vote_id: Vote ID

        Returns:
            List of quality IDs
        """
        results = (
            self.db.query(VoteQuality.quality_id)
            .filter(VoteQuality.vote_id == vote_id)
            .all()
        )
        return [r[0] for r in results]

    def set_qualities(self, vote_id: int, quality_ids: list[int]) -> list[VoteQuality]:
        """
        Replace all qualities for a vote.

        Args:
            vote_id: Vote ID
            quality_ids: List of quality IDs to attach

        Returns:
            List of newly created VoteQuality records
        """
        # Delete existing
        self.db.query(VoteQuality).filter(VoteQuality.vote_id == vote_id).delete()

        # Add new (deduplicated)
        unique_ids = list(set(quality_ids))
        new_qualities = [
            VoteQuality(vote_id=vote_id, quality_id=qid) for qid in unique_ids
        ]
        self.db.add_all(new_qualities)
        self.db.flush()
        return new_qualities

    def clear_qualities(self, vote_id: int) -> None:
        """
        Remove all qualities from a vote.

        Args:
            vote_id: Vote ID
        """
        self.db.query(VoteQuality).filter(VoteQuality.vote_id == vote_id).delete()

    def get_counts_for_idea(self, idea_id: int) -> dict[int, int]:
        """
        Get aggregated quality counts for an idea.

        Only counts qualities from upvotes.

        Args:
            idea_id: Idea ID

        Returns:
            Dictionary mapping quality_id to count
        """
        result = (
            self.db.query(
                VoteQuality.quality_id, func.count(VoteQuality.id).label("count")
            )
            .join(Vote, VoteQuality.vote_id == Vote.id)
            .filter(Vote.idea_id == idea_id, Vote.vote_type == VoteType.UPVOTE)
            .group_by(VoteQuality.quality_id)
            .all()
        )

        return {quality_id: count for quality_id, count in result}

    def get_detailed_counts_for_idea(self, idea_id: int) -> list[dict]:
        """
        Get quality counts with quality info for an idea.

        Only counts qualities from upvotes.

        Args:
            idea_id: Idea ID

        Returns:
            List of dicts with quality_id, quality_key, and count
        """
        result = (
            self.db.query(
                VoteQuality.quality_id,
                Quality.key,
                func.count(VoteQuality.id).label("count"),
            )
            .join(Vote, VoteQuality.vote_id == Vote.id)
            .join(Quality, VoteQuality.quality_id == Quality.id)
            .filter(Vote.idea_id == idea_id, Vote.vote_type == VoteType.UPVOTE)
            .group_by(VoteQuality.quality_id, Quality.key)
            .all()
        )

        return [
            {"quality_id": qid, "quality_key": key, "count": count}
            for qid, key, count in result
        ]

    def count_votes_with_qualities(self, idea_id: int) -> int:
        """
        Count how many upvotes on this idea have at least one quality.

        Args:
            idea_id: Idea ID

        Returns:
            Count of votes with at least one quality
        """
        result = (
            self.db.query(func.count(func.distinct(VoteQuality.vote_id)))
            .join(Vote, VoteQuality.vote_id == Vote.id)
            .filter(Vote.idea_id == idea_id, Vote.vote_type == VoteType.UPVOTE)
            .scalar()
        )
        return result or 0

    def get_counts_for_ideas_batch(self, idea_ids: list[int]) -> dict[int, dict]:
        """
        Get quality counts for multiple ideas in a single query.

        Args:
            idea_ids: List of idea IDs

        Returns:
            Dictionary mapping idea_id to quality counts data
        """
        if not idea_ids:
            return {}

        # Get all quality counts for all ideas in one query
        result = (
            self.db.query(
                Vote.idea_id,
                VoteQuality.quality_id,
                Quality.key,
                func.count(VoteQuality.id).label("count"),
            )
            .join(Vote, VoteQuality.vote_id == Vote.id)
            .join(Quality, VoteQuality.quality_id == Quality.id)
            .filter(Vote.idea_id.in_(idea_ids), Vote.vote_type == VoteType.UPVOTE)
            .group_by(Vote.idea_id, VoteQuality.quality_id, Quality.key)
            .all()
        )

        # Get count of votes with qualities per idea
        votes_with_qualities = (
            self.db.query(
                Vote.idea_id,
                func.count(func.distinct(VoteQuality.vote_id)).label("total"),
            )
            .join(VoteQuality, VoteQuality.vote_id == Vote.id)
            .filter(Vote.idea_id.in_(idea_ids), Vote.vote_type == VoteType.UPVOTE)
            .group_by(Vote.idea_id)
            .all()
        )

        # Build result dictionary
        totals_map = {idea_id: total for idea_id, total in votes_with_qualities}

        counts_by_idea: dict[int, dict] = {}
        for idea_id, quality_id, quality_key, count in result:
            if idea_id not in counts_by_idea:
                counts_by_idea[idea_id] = {
                    "counts": [],
                    "total_votes_with_qualities": totals_map.get(idea_id, 0),
                }
            counts_by_idea[idea_id]["counts"].append(
                {"quality_id": quality_id, "quality_key": quality_key, "count": count}
            )

        # Ensure all requested ideas have an entry
        for idea_id in idea_ids:
            if idea_id not in counts_by_idea:
                counts_by_idea[idea_id] = {
                    "counts": [],
                    "total_votes_with_qualities": 0,
                }

        return counts_by_idea
