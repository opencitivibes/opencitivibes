"""
Quality Signals Service - Aggregate quality signals for ideas.

Combines trust distribution and vote quality data for public and admin views.
"""

from sqlalchemy.orm import Session

from models.schemas import (
    QualityCounts,
    QualitySignalsResponse,
    TrustDistribution,
)
from repositories.vote_quality_repository import VoteQualityRepository
from repositories.vote_repository import VoteRepository


class QualitySignalsService:
    """Service for aggregating quality signals for ideas."""

    @staticmethod
    def get_signals_for_idea(db: Session, idea_id: int) -> QualitySignalsResponse:
        """
        Get aggregated quality signals for an idea.

        Combines trust distribution and vote quality counts.

        Args:
            db: Database session
            idea_id: Idea ID

        Returns:
            QualitySignalsResponse with trust distribution and quality counts
        """
        vote_repo = VoteRepository(db)
        vote_quality_repo = VoteQualityRepository(db)

        # Get trust distribution from votes
        trust_data = vote_repo.get_trust_distribution_for_idea(idea_id)

        # Get quality counts
        quality_counts_data = vote_quality_repo.get_detailed_counts_for_idea(idea_id)
        votes_with_qualities = vote_quality_repo.count_votes_with_qualities(idea_id)

        # Build response
        trust_distribution = TrustDistribution(
            excellent=trust_data["excellent"],
            good=trust_data["good"],
            average=trust_data["average"],
            below_average=trust_data["below_average"],
            low=trust_data["low"],
            total_votes=trust_data["total_votes"],
        )

        from models.schemas import QualityCount

        quality_counts = QualityCounts(
            counts=[
                QualityCount(
                    quality_id=q["quality_id"],
                    quality_key=q["quality_key"],
                    count=q["count"],
                )
                for q in quality_counts_data
            ],
            total_votes_with_qualities=votes_with_qualities,
        )

        return QualitySignalsResponse(
            trust_distribution=trust_distribution,
            quality_counts=quality_counts,
            votes_with_qualities=votes_with_qualities,
            total_upvotes=trust_data["total_votes"],
        )

    @staticmethod
    def get_signals_batch(
        db: Session, idea_ids: list[int]
    ) -> dict[int, QualitySignalsResponse]:
        """
        Get quality signals for multiple ideas efficiently.

        Uses batch queries to prevent N+1 problem.

        Args:
            db: Database session
            idea_ids: List of idea IDs

        Returns:
            Dict mapping idea_id to QualitySignalsResponse
        """
        if not idea_ids:
            return {}

        vote_repo = VoteRepository(db)
        vote_quality_repo = VoteQualityRepository(db)

        # Get trust distributions for all ideas
        trust_distributions = vote_repo.get_trust_distribution_batch(idea_ids)

        # Get quality counts for all ideas
        quality_counts_batch = vote_quality_repo.get_counts_for_ideas_batch(idea_ids)

        # Build responses for each idea
        result: dict[int, QualitySignalsResponse] = {}
        for idea_id in idea_ids:
            trust_data = trust_distributions.get(
                idea_id,
                {
                    "excellent": 0,
                    "good": 0,
                    "average": 0,
                    "below_average": 0,
                    "low": 0,
                    "total_votes": 0,
                },
            )

            quality_data = quality_counts_batch.get(
                idea_id, {"counts": [], "total_votes_with_qualities": 0}
            )

            trust_distribution = TrustDistribution(
                excellent=trust_data["excellent"],
                good=trust_data["good"],
                average=trust_data["average"],
                below_average=trust_data["below_average"],
                low=trust_data["low"],
                total_votes=trust_data["total_votes"],
            )

            from models.schemas import QualityCount

            quality_counts = QualityCounts(
                counts=[
                    QualityCount(
                        quality_id=q["quality_id"],
                        quality_key=q["quality_key"],
                        count=q["count"],
                    )
                    for q in quality_data.get("counts", [])
                ],
                total_votes_with_qualities=quality_data.get(
                    "total_votes_with_qualities", 0
                ),
            )

            result[idea_id] = QualitySignalsResponse(
                trust_distribution=trust_distribution,
                quality_counts=quality_counts,
                votes_with_qualities=quality_data.get("total_votes_with_qualities", 0),
                total_upvotes=trust_data["total_votes"],
            )

        return result
