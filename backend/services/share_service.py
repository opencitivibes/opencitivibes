"""
Share service for business logic.

Handles share event recording and analytics retrieval.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from models.exceptions import IdeaNotFoundException
from models.schemas import (
    AdminShareAnalyticsResponse,
    ShareAnalyticsResponse,
    ShareEventResponse,
    SharePlatform,
    TopSharedIdea,
)
from repositories.idea_repository import IdeaRepository
from repositories.share_repository import ShareRepository


class ShareService:
    """Service for share-related business logic."""

    @staticmethod
    def record_share(
        db: Session,
        idea_id: int,
        platform: SharePlatform,
        referrer_url: str | None = None,
    ) -> ShareEventResponse:
        """
        Record a share event for an idea.

        Args:
            db: Database session
            idea_id: ID of the shared idea
            platform: Social media platform
            referrer_url: Optional URL where share was initiated

        Returns:
            ShareEventResponse with created event details

        Raises:
            IdeaNotFoundException: If idea does not exist
        """
        idea_repo = IdeaRepository(db)
        share_repo = ShareRepository(db)

        # Validate idea exists
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise IdeaNotFoundException(f"Idea with ID {idea_id} not found")

        # Convert schema enum to db enum
        db_platform = db_models.SharePlatform(platform.value)

        # Record the share event
        share_event = share_repo.create_share_event(
            idea_id=idea_id,
            platform=db_platform,
            referrer_url=referrer_url,
        )

        return ShareEventResponse(
            id=share_event.id,
            idea_id=share_event.idea_id,
            platform=SharePlatform(share_event.platform.value),
            created_at=share_event.created_at,
        )

    @staticmethod
    def get_idea_share_analytics(db: Session, idea_id: int) -> ShareAnalyticsResponse:
        """
        Get share analytics for a specific idea.

        Args:
            db: Database session
            idea_id: ID of the idea

        Returns:
            ShareAnalyticsResponse with share statistics

        Raises:
            IdeaNotFoundException: If idea does not exist
        """
        idea_repo = IdeaRepository(db)
        share_repo = ShareRepository(db)

        # Validate idea exists
        idea = idea_repo.get_by_id(idea_id)
        if not idea:
            raise IdeaNotFoundException(f"Idea with ID {idea_id} not found")

        # Get share counts
        counts = share_repo.get_share_counts_by_idea(idea_id)
        last_7_days = share_repo.get_recent_share_count(idea_id, days=7)

        return ShareAnalyticsResponse(
            idea_id=idea_id,
            total_shares=counts["total_shares"],
            by_platform=counts["by_platform"],
            last_7_days=last_7_days,
        )

    @staticmethod
    def get_top_shared_ideas(db: Session, limit: int = 10) -> list[TopSharedIdea]:
        """
        Get top shared ideas.

        Args:
            db: Database session
            limit: Maximum number of results

        Returns:
            List of TopSharedIdea objects
        """
        share_repo = ShareRepository(db)
        top_ideas = share_repo.get_top_shared_ideas(limit=limit)

        return [
            TopSharedIdea(
                idea_id=idea["idea_id"],
                title=idea["title"],
                total_shares=idea["total_shares"],
                by_platform=idea["by_platform"],
            )
            for idea in top_ideas
        ]

    @staticmethod
    def get_admin_share_analytics(db: Session) -> AdminShareAnalyticsResponse:
        """
        Get admin share analytics overview.

        Args:
            db: Database session

        Returns:
            AdminShareAnalyticsResponse with complete analytics
        """
        share_repo = ShareRepository(db)

        total_shares = share_repo.get_total_shares()
        platform_distribution = share_repo.get_platform_distribution()
        top_ideas = ShareService.get_top_shared_ideas(db, limit=10)
        shares_last_7_days = share_repo.get_total_shares(days=7)
        shares_last_30_days = share_repo.get_total_shares(days=30)

        return AdminShareAnalyticsResponse(
            total_shares=total_shares,
            platform_distribution=platform_distribution,
            top_shared_ideas=top_ideas,
            shares_last_7_days=shares_last_7_days,
            shares_last_30_days=shares_last_30_days,
            generated_at=datetime.now(timezone.utc),
        )
