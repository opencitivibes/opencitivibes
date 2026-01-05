"""Sitemap service for SEO optimization.

Provides lightweight data retrieval for sitemap generation.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from repositories.idea_repository import IdeaRepository


class SitemapIdeaData:
    """Lightweight idea data for sitemap."""

    def __init__(self, id: int, updated_at: datetime, score: int) -> None:
        self.id = id
        self.updated_at = updated_at
        self.score = score


class SitemapService:
    """Service for sitemap-related operations."""

    @staticmethod
    def _get_updated_at(updated_at: Optional[datetime]) -> datetime:
        """Get updated_at with fallback to current time if None."""
        return updated_at if updated_at else datetime.now(timezone.utc)

    @staticmethod
    def get_sitemap_ideas(db: Session) -> list[SitemapIdeaData]:
        """Get all approved ideas for sitemap generation.

        Returns minimal data needed for sitemap:
        - id: for URL generation
        - updated_at: for lastmod
        - score: for priority calculation
        """
        idea_repo = IdeaRepository(db)
        sitemap_data = idea_repo.get_sitemap_data()

        return [
            SitemapIdeaData(
                id=id,
                updated_at=SitemapService._get_updated_at(updated_at),
                score=score,
            )
            for id, updated_at, score in sitemap_data
        ]
