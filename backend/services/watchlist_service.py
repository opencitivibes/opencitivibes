"""
Service for keyword watchlist business logic.
"""

import re

from sqlalchemy.orm import Session

from models.exceptions import (
    DuplicateKeywordException,
    InvalidRegexException,
    KeywordNotFoundException,
)
from repositories.db_models import (
    ContentFlag,
    ContentType,
    FlagReason,
    KeywordWatchlist,
)


class WatchlistService:
    """Service for keyword watchlist operations."""

    @staticmethod
    def check_content_for_keywords(
        db: Session,
        content: str,
        content_type: ContentType,
        content_id: int,
    ) -> list[ContentFlag]:
        """
        Check content against watchlist and create auto-flags for matches.

        Args:
            db: Database session
            content: Text content to check
            content_type: Type of content
            content_id: ID of content

        Returns:
            List of created auto-flags
        """
        from repositories.watchlist_repository import WatchlistRepository

        watchlist_repo = WatchlistRepository(db)
        keywords = watchlist_repo.get_active_keywords()

        content_lower = content.lower()
        created_flags: list[ContentFlag] = []

        for keyword in keywords:
            matched = False

            if keyword.is_regex:
                try:
                    if re.search(keyword.keyword, content, re.IGNORECASE):
                        matched = True
                except re.error:
                    # Skip invalid regex
                    continue
            else:
                if keyword.keyword.lower() in content_lower:
                    matched = True

            if matched:
                # Create auto-flag
                flag = watchlist_repo.create_auto_flag(
                    content_type=content_type,
                    content_id=content_id,
                    keyword=str(keyword.keyword),
                    reason=keyword.auto_flag_reason,  # type: ignore[arg-type]
                )

                # Increment match count
                watchlist_repo.increment_match_count(keyword)

                created_flags.append(flag)

        if created_flags:
            watchlist_repo.commit_and_refresh_flags(created_flags)

        return created_flags

    @staticmethod
    def add_keyword(
        db: Session,
        keyword: str,
        created_by: int,
        is_regex: bool = False,
        auto_flag_reason: FlagReason = FlagReason.SPAM,
    ) -> KeywordWatchlist:
        """
        Add a keyword to the watchlist.

        Args:
            db: Database session
            keyword: Keyword or regex pattern
            created_by: Admin user ID
            is_regex: Whether this is a regex pattern
            auto_flag_reason: Reason to use for auto-flags

        Returns:
            Created keyword entry

        Raises:
            DuplicateKeywordException: If keyword already exists
            InvalidRegexException: If regex pattern is invalid
        """
        from repositories.watchlist_repository import WatchlistRepository

        watchlist_repo = WatchlistRepository(db)

        # Check for duplicate
        existing = watchlist_repo.get_by_keyword(keyword)
        if existing:
            raise DuplicateKeywordException(keyword)

        # Validate regex if applicable
        if is_regex:
            try:
                re.compile(keyword)
            except re.error as e:
                raise InvalidRegexException(keyword, str(e))

        entry = KeywordWatchlist(
            keyword=keyword,
            is_regex=is_regex,
            auto_flag_reason=auto_flag_reason,
            is_active=True,
            created_by=created_by,
        )
        watchlist_repo.add(entry)
        watchlist_repo.commit()
        watchlist_repo.refresh(entry)
        return entry

    @staticmethod
    def update_keyword(
        db: Session,
        keyword_id: int,
        is_regex: bool | None = None,
        auto_flag_reason: FlagReason | None = None,
        is_active: bool | None = None,
    ) -> KeywordWatchlist:
        """
        Update a keyword entry.

        Args:
            db: Database session
            keyword_id: ID of keyword to update
            is_regex: New regex flag (optional)
            auto_flag_reason: New flag reason (optional)
            is_active: New active status (optional)

        Returns:
            Updated keyword entry

        Raises:
            KeywordNotFoundException: If keyword not found
            InvalidRegexException: If new regex pattern is invalid
        """
        from repositories.watchlist_repository import WatchlistRepository

        watchlist_repo = WatchlistRepository(db)
        entry = watchlist_repo.get_by_id(keyword_id)
        if not entry:
            raise KeywordNotFoundException(keyword_id)

        if is_regex is not None:
            if is_regex:
                try:
                    re.compile(entry.keyword)
                except re.error as e:
                    raise InvalidRegexException(entry.keyword, str(e))
            entry.is_regex = is_regex  # type: ignore[assignment]

        if auto_flag_reason is not None:
            entry.auto_flag_reason = auto_flag_reason  # type: ignore[assignment]

        if is_active is not None:
            entry.is_active = is_active  # type: ignore[assignment]

        watchlist_repo.commit()
        watchlist_repo.refresh(entry)
        return entry

    @staticmethod
    def delete_keyword(db: Session, keyword_id: int) -> None:
        """
        Delete a keyword from watchlist.

        Args:
            db: Database session
            keyword_id: ID of keyword to delete

        Raises:
            KeywordNotFoundException: If keyword not found
        """
        from repositories.watchlist_repository import WatchlistRepository

        watchlist_repo = WatchlistRepository(db)
        entry = watchlist_repo.get_by_id(keyword_id)
        if not entry:
            raise KeywordNotFoundException(keyword_id)

        watchlist_repo.delete(entry)
        watchlist_repo.commit()

    @staticmethod
    def get_all_keywords(
        db: Session,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[KeywordWatchlist]:
        """
        Get all keywords in watchlist.

        Args:
            db: Database session
            active_only: Only return active keywords
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of keyword entries
        """
        from repositories.watchlist_repository import WatchlistRepository

        watchlist_repo = WatchlistRepository(db)
        return watchlist_repo.get_all_filtered(
            active_only=active_only,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def test_keyword(keyword: str, test_text: str) -> bool:
        """
        Test if a keyword/regex would match given text.

        Args:
            keyword: Keyword or regex pattern
            test_text: Text to test against

        Returns:
            True if matches, False otherwise
        """
        # First try as regex
        try:
            if re.search(keyword, test_text, re.IGNORECASE):
                return True
        except re.error:
            pass

        # Fall back to plain text
        return keyword.lower() in test_text.lower()
