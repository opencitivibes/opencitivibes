"""
Vote service for business logic.
"""

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from models.exceptions import (
    BusinessRuleException,
    IdeaNotFoundException,
    VoteNotFoundException,
)
from repositories.idea_repository import IdeaRepository
from repositories.vote_quality_repository import VoteQualityRepository
from repositories.vote_repository import VoteRepository
from services.quality_service import QualityService


class VoteService:
    """Service for vote-related business logic."""

    @staticmethod
    def vote_on_idea(
        db: Session,
        idea_id: int,
        user_id: int,
        vote_type: db_models.VoteType,
        quality_ids: list[int] | None = None,
    ) -> db_models.Vote:
        """
        Vote on an idea with optional qualities.

        Args:
            db: Database session
            idea_id: Idea ID
            user_id: User ID
            vote_type: Vote type (UPVOTE or DOWNVOTE)
            quality_ids: Optional list of quality IDs (only for upvotes)

        Returns:
            Created or updated vote

        Raises:
            IdeaNotFoundException: If idea not found
            BusinessRuleException: If idea is not approved or user is the author
        """
        idea_repo = IdeaRepository(db)
        vote_repo = VoteRepository(db)
        vote_quality_repo = VoteQualityRepository(db)

        # Check if idea exists and is approved
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise IdeaNotFoundException(f"Idea with ID {idea_id} not found")

        if idea.status != db_models.IdeaStatus.APPROVED:
            raise BusinessRuleException("Can only vote on approved ideas")

        # Check if user is trying to vote on their own idea
        if idea.user_id == user_id:
            raise BusinessRuleException("Cannot vote on your own idea")

        # Business rule: qualities only for upvotes
        if vote_type != db_models.VoteType.UPVOTE:
            quality_ids = None

        # Validate quality IDs against category
        if quality_ids:
            quality_ids = QualityService.validate_quality_ids(
                db, quality_ids, idea.category_id
            )

        # Check if user already voted
        existing_vote = vote_repo.get_by_idea_and_user(idea_id, user_id)

        if existing_vote:
            # Update existing vote
            existing_vote.vote_type = vote_type
            vote = vote_repo.update(existing_vote)

            # Clear qualities if switching to downvote
            if vote_type == db_models.VoteType.DOWNVOTE:
                vote_quality_repo.clear_qualities(vote.id)
            elif quality_ids:
                vote_quality_repo.set_qualities(vote.id, quality_ids)
        else:
            # Create new vote
            new_vote = db_models.Vote(
                idea_id=idea_id, user_id=user_id, vote_type=vote_type
            )
            vote = vote_repo.create(new_vote)

            # Add qualities for upvotes
            if vote_type == db_models.VoteType.UPVOTE and quality_ids:
                vote_quality_repo.set_qualities(vote.id, quality_ids)

        return vote

    @staticmethod
    def update_vote_qualities(
        db: Session, idea_id: int, user_id: int, quality_ids: list[int]
    ) -> list[int]:
        """
        Update qualities for an existing upvote.

        Args:
            db: Database session
            idea_id: Idea ID
            user_id: User ID
            quality_ids: List of quality IDs to set

        Returns:
            List of quality IDs that were set

        Raises:
            VoteNotFoundException: If no vote found
            BusinessRuleException: If vote is not an upvote
        """
        vote_repo = VoteRepository(db)
        vote_quality_repo = VoteQualityRepository(db)
        idea_repo = IdeaRepository(db)

        vote = vote_repo.get_by_idea_and_user(idea_id, user_id)
        if not vote:
            raise VoteNotFoundException(f"No vote found for idea {idea_id}")

        if vote.vote_type != db_models.VoteType.UPVOTE:
            raise BusinessRuleException("Qualities can only be added to upvotes")

        # Get idea for category validation
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise IdeaNotFoundException(f"Idea with ID {idea_id} not found")

        validated_ids = QualityService.validate_quality_ids(
            db, quality_ids, idea.category_id
        )

        vote_quality_repo.set_qualities(vote.id, validated_ids)
        return validated_ids

    @staticmethod
    def get_vote_qualities(db: Session, idea_id: int, user_id: int) -> list[int]:
        """
        Get user's quality selections for their vote on an idea.

        Args:
            db: Database session
            idea_id: Idea ID
            user_id: User ID

        Returns:
            List of quality IDs (empty if no vote or downvote)
        """
        vote_repo = VoteRepository(db)
        vote_quality_repo = VoteQualityRepository(db)

        vote = vote_repo.get_by_idea_and_user(idea_id, user_id)
        if not vote or vote.vote_type != db_models.VoteType.UPVOTE:
            return []

        return vote_quality_repo.get_quality_ids_by_vote(vote.id)

    @staticmethod
    def remove_vote(db: Session, idea_id: int, user_id: int) -> None:
        """
        Remove a user's vote on an idea.

        Args:
            db: Database session
            idea_id: Idea ID
            user_id: User ID

        Raises:
            VoteNotFoundException: If vote not found
        """
        vote_repo = VoteRepository(db)

        vote = vote_repo.get_by_idea_and_user(idea_id, user_id)
        if not vote:
            raise VoteNotFoundException(
                f"Vote not found for idea {idea_id} and user {user_id}"
            )

        # VoteQuality records are deleted via cascade
        vote_repo.delete(vote)

    @staticmethod
    def get_user_vote(db: Session, idea_id: int, user_id: int) -> db_models.Vote | None:
        """
        Get user's vote on an idea.

        Args:
            db: Database session
            idea_id: Idea ID
            user_id: User ID

        Returns:
            Vote if found, None otherwise
        """
        vote_repo = VoteRepository(db)
        return vote_repo.get_by_idea_and_user(idea_id, user_id)
