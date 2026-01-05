"""
Repository for keyword watchlist database operations.
"""

from sqlalchemy.orm import Session

from repositories.base import BaseRepository
from repositories.db_models import (
    ContentFlag,
    ContentType,
    FlagReason,
    FlagStatus,
    KeywordWatchlist,
)


# System user ID for auto-flags
SYSTEM_USER_ID = 1


class WatchlistRepository(BaseRepository[KeywordWatchlist]):
    """Repository for KeywordWatchlist entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize watchlist repository.

        Args:
            db: Database session
        """
        super().__init__(KeywordWatchlist, db)

    def get_active_keywords(self) -> list[KeywordWatchlist]:
        """
        Get all active keywords.

        Returns:
            List of active keyword entries
        """
        return (
            self.db.query(KeywordWatchlist)
            .filter(KeywordWatchlist.is_active == True)  # noqa: E712
            .all()
        )

    def get_by_keyword(self, keyword: str) -> KeywordWatchlist | None:
        """
        Get keyword entry by keyword text.

        Args:
            keyword: Keyword text to find

        Returns:
            Keyword entry if found, None otherwise
        """
        return (
            self.db.query(KeywordWatchlist)
            .filter(KeywordWatchlist.keyword == keyword)
            .first()
        )

    def get_all_filtered(
        self,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[KeywordWatchlist]:
        """
        Get all keywords with optional filters.

        Args:
            active_only: Only return active keywords
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of keyword entries
        """
        query = self.db.query(KeywordWatchlist)

        if active_only:
            query = query.filter(KeywordWatchlist.is_active == True)  # noqa: E712

        return (
            query.order_by(KeywordWatchlist.match_count.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_auto_flag(
        self,
        content_type: ContentType,
        content_id: int,
        keyword: str,
        reason: FlagReason,
    ) -> ContentFlag:
        """
        Create an auto-flag for content matching a keyword.

        Args:
            content_type: Type of content (IDEA or COMMENT)
            content_id: ID of the flagged content
            keyword: Keyword that triggered the flag
            reason: Flag reason from the keyword

        Returns:
            Created ContentFlag
        """
        flag = ContentFlag(
            content_type=content_type,
            content_id=content_id,
            reporter_id=SYSTEM_USER_ID,
            reason=reason,
            details=f"Auto-flagged: keyword match '{keyword}'",
            status=FlagStatus.PENDING,
        )
        self.db.add(flag)
        return flag

    def increment_match_count(self, keyword: KeywordWatchlist) -> None:
        """
        Increment the match count for a keyword.

        Args:
            keyword: Keyword entry to update
        """
        keyword.match_count = (keyword.match_count or 0) + 1  # type: ignore[assignment]

    def commit_and_refresh_flags(self, flags: list[ContentFlag]) -> None:
        """
        Commit transaction and refresh all flags.

        Args:
            flags: List of flags to refresh
        """
        self.db.commit()
        for flag in flags:
            self.db.refresh(flag)
