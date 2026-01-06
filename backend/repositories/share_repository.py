"""
Share repository for database operations.

Handles all database interactions for share event tracking.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

import repositories.db_models as db_models
from .base import BaseRepository


class ShareRepository(BaseRepository[db_models.ShareEvent]):
    """Repository for ShareEvent entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize share repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.ShareEvent, db)

    def create_share_event(
        self,
        idea_id: int,
        platform: db_models.SharePlatform,
        referrer_url: str | None = None,
    ) -> db_models.ShareEvent:
        """
        Create a new share event.

        Args:
            idea_id: ID of the shared idea
            platform: Social media platform
            referrer_url: Optional URL where share was initiated

        Returns:
            Created ShareEvent
        """
        share_event = db_models.ShareEvent(
            idea_id=idea_id,
            platform=platform,
            referrer_url=referrer_url,
        )
        return self.create(share_event)

    def get_share_counts_by_idea(self, idea_id: int) -> dict[str, Any]:
        """
        Get share counts for a specific idea.

        Args:
            idea_id: ID of the idea

        Returns:
            Dict with total_shares and by_platform counts
        """
        counts = (
            self.db.query(
                db_models.ShareEvent.platform,
                func.count(db_models.ShareEvent.id).label("count"),
            )
            .filter(db_models.ShareEvent.idea_id == idea_id)
            .group_by(db_models.ShareEvent.platform)
            .all()
        )

        by_platform: dict[str, int] = {
            row.platform.value: row.count
            for row in counts  # type: ignore[misc]
        }
        total = sum(by_platform.values())

        return {
            "total_shares": total,
            "by_platform": by_platform,
        }

    def get_recent_share_count(self, idea_id: int, days: int = 7) -> int:
        """
        Get share count for recent period.

        Args:
            idea_id: ID of the idea
            days: Number of days to look back

        Returns:
            Number of shares in the period
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        return (
            self.db.query(func.count(db_models.ShareEvent.id))
            .filter(
                db_models.ShareEvent.idea_id == idea_id,
                db_models.ShareEvent.created_at >= cutoff,
            )
            .scalar()
            or 0
        )

    def get_share_counts_by_idea_batch(
        self, idea_ids: list[int]
    ) -> dict[int, dict[str, Any]]:
        """
        Get share counts for multiple ideas in a single query.

        Args:
            idea_ids: List of idea IDs

        Returns:
            Dict mapping idea_id to {total_shares, by_platform}
        """
        if not idea_ids:
            return {}

        # Get counts grouped by idea and platform
        counts = (
            self.db.query(
                db_models.ShareEvent.idea_id,
                db_models.ShareEvent.platform,
                func.count(db_models.ShareEvent.id).label("count"),
            )
            .filter(db_models.ShareEvent.idea_id.in_(idea_ids))
            .group_by(db_models.ShareEvent.idea_id, db_models.ShareEvent.platform)
            .all()
        )

        # Build result dict
        result: dict[int, dict[str, Any]] = {}
        for row in counts:
            idea_id = row.idea_id
            if idea_id not in result:
                result[idea_id] = {"total_shares": 0, "by_platform": {}}
            result[idea_id]["by_platform"][row.platform.value] = row.count
            result[idea_id]["total_shares"] += row.count

        # Fill in zeros for ideas with no shares
        for idea_id in idea_ids:
            if idea_id not in result:
                result[idea_id] = {"total_shares": 0, "by_platform": {}}

        return result

    def get_total_shares(self, days: int | None = None) -> int:
        """
        Get total number of shares.

        Args:
            days: Optional limit to recent days

        Returns:
            Total share count
        """
        query = self.db.query(func.count(db_models.ShareEvent.id))
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(db_models.ShareEvent.created_at >= cutoff)
        return query.scalar() or 0

    def get_platform_distribution(self, days: int | None = None) -> dict[str, int]:
        """
        Get distribution of shares across platforms.

        Args:
            days: Optional limit to recent days

        Returns:
            Dict mapping platform to count
        """
        query = self.db.query(
            db_models.ShareEvent.platform,
            func.count(db_models.ShareEvent.id).label("count"),
        )
        if days:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(db_models.ShareEvent.created_at >= cutoff)
        query = query.group_by(db_models.ShareEvent.platform)

        return {  # type: ignore[invalid-return-type]
            row.platform.value: row.count for row in query.all()
        }

    def get_top_shared_ideas(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get top shared ideas with their share counts.

        Args:
            limit: Maximum number of results

        Returns:
            List of dicts with idea_id, title, total_shares, by_platform
        """
        # Get top ideas by share count
        top_ideas = (
            self.db.query(
                db_models.ShareEvent.idea_id,
                db_models.Idea.title,
                func.count(db_models.ShareEvent.id).label("total_shares"),
            )
            .join(db_models.Idea, db_models.ShareEvent.idea_id == db_models.Idea.id)
            .filter(db_models.Idea.deleted_at.is_(None))
            .group_by(db_models.ShareEvent.idea_id, db_models.Idea.title)
            .order_by(func.count(db_models.ShareEvent.id).desc())
            .limit(limit)
            .all()
        )

        if not top_ideas:
            return []

        # Get platform breakdown for these ideas
        idea_ids = [row.idea_id for row in top_ideas]
        platform_counts = self.get_share_counts_by_idea_batch(idea_ids)

        result = []
        for row in top_ideas:
            result.append(
                {
                    "idea_id": row.idea_id,
                    "title": row.title,
                    "total_shares": row.total_shares,
                    "by_platform": platform_counts.get(row.idea_id, {}).get(
                        "by_platform", {}
                    ),
                }
            )

        return result
