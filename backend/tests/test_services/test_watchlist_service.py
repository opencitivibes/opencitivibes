"""
Unit tests for WatchlistService.
"""

import pytest
from sqlalchemy.orm import Session

from models.exceptions import (
    DuplicateKeywordException,
    InvalidRegexException,
    KeywordNotFoundException,
)
from repositories.db_models import (
    ContentType,
    FlagReason,
    FlagStatus,
    Idea,
    KeywordWatchlist,
    User,
)
from services.watchlist_service import WatchlistService


class TestAddKeyword:
    """Tests for WatchlistService.add_keyword."""

    def test_add_simple_keyword(self, db_session: Session, admin_user: User):
        """Should add a simple keyword to watchlist."""
        result = WatchlistService.add_keyword(db_session, "spam", admin_user.id)

        assert result.keyword == "spam"
        assert result.is_regex is False
        assert result.is_active is True
        assert result.auto_flag_reason == FlagReason.SPAM
        assert result.created_by == admin_user.id

    def test_add_keyword_with_custom_reason(
        self, db_session: Session, admin_user: User
    ):
        """Should add keyword with custom flag reason."""
        result = WatchlistService.add_keyword(
            db_session,
            "hateful",
            admin_user.id,
            auto_flag_reason=FlagReason.HATE_SPEECH,
        )

        assert result.keyword == "hateful"
        assert result.auto_flag_reason == FlagReason.HATE_SPEECH

    def test_add_regex_keyword(self, db_session: Session, admin_user: User):
        """Should add a valid regex pattern."""
        result = WatchlistService.add_keyword(
            db_session,
            r"\bspam\b",
            admin_user.id,
            is_regex=True,
        )

        assert result.keyword == r"\bspam\b"
        assert result.is_regex is True

    def test_add_invalid_regex_raises_exception(
        self, db_session: Session, admin_user: User
    ):
        """Should raise InvalidRegexException for invalid regex."""
        with pytest.raises(InvalidRegexException) as exc_info:
            WatchlistService.add_keyword(
                db_session,
                r"[invalid",  # Invalid regex
                admin_user.id,
                is_regex=True,
            )

        assert "[invalid" in str(exc_info.value)

    def test_add_duplicate_keyword_raises_exception(
        self, db_session: Session, admin_user: User
    ):
        """Should raise DuplicateKeywordException for duplicate."""
        WatchlistService.add_keyword(db_session, "duplicate", admin_user.id)

        with pytest.raises(DuplicateKeywordException) as exc_info:
            WatchlistService.add_keyword(db_session, "duplicate", admin_user.id)

        assert exc_info.value.keyword == "duplicate"


class TestUpdateKeyword:
    """Tests for WatchlistService.update_keyword."""

    def test_update_is_active(self, db_session: Session, admin_user: User):
        """Should update is_active status."""
        keyword = WatchlistService.add_keyword(db_session, "test", admin_user.id)

        result = WatchlistService.update_keyword(
            db_session, keyword.id, is_active=False
        )

        assert result.is_active is False

    def test_update_auto_flag_reason(self, db_session: Session, admin_user: User):
        """Should update auto_flag_reason."""
        keyword = WatchlistService.add_keyword(db_session, "test", admin_user.id)

        result = WatchlistService.update_keyword(
            db_session, keyword.id, auto_flag_reason=FlagReason.HATE_SPEECH
        )

        assert result.auto_flag_reason == FlagReason.HATE_SPEECH

    def test_update_is_regex(self, db_session: Session, admin_user: User):
        """Should update is_regex flag."""
        keyword = WatchlistService.add_keyword(db_session, "simple", admin_user.id)

        result = WatchlistService.update_keyword(db_session, keyword.id, is_regex=True)

        assert result.is_regex is True

    def test_update_nonexistent_keyword_raises_exception(self, db_session: Session):
        """Should raise KeywordNotFoundException for non-existent keyword."""
        with pytest.raises(KeywordNotFoundException) as exc_info:
            WatchlistService.update_keyword(db_session, 99999, is_active=False)

        assert exc_info.value.keyword_id == 99999

    def test_update_to_invalid_regex_raises_exception(
        self, db_session: Session, admin_user: User
    ):
        """Should raise InvalidRegexException when converting invalid pattern to regex."""
        keyword = WatchlistService.add_keyword(
            db_session, "[invalid", admin_user.id, is_regex=False
        )

        with pytest.raises(InvalidRegexException):
            WatchlistService.update_keyword(db_session, keyword.id, is_regex=True)


class TestDeleteKeyword:
    """Tests for WatchlistService.delete_keyword."""

    def test_delete_keyword(self, db_session: Session, admin_user: User):
        """Should delete keyword from watchlist."""
        keyword = WatchlistService.add_keyword(db_session, "todelete", admin_user.id)
        keyword_id = keyword.id

        WatchlistService.delete_keyword(db_session, keyword_id)

        # Verify deleted
        result = db_session.query(KeywordWatchlist).filter_by(id=keyword_id).first()
        assert result is None

    def test_delete_nonexistent_keyword_raises_exception(self, db_session: Session):
        """Should raise KeywordNotFoundException for non-existent keyword."""
        with pytest.raises(KeywordNotFoundException) as exc_info:
            WatchlistService.delete_keyword(db_session, 99999)

        assert exc_info.value.keyword_id == 99999


class TestGetAllKeywords:
    """Tests for WatchlistService.get_all_keywords."""

    def test_get_all_keywords_empty(self, db_session: Session):
        """Should return empty list when no keywords exist."""
        result = WatchlistService.get_all_keywords(db_session)
        assert result == []

    def test_get_all_keywords(self, db_session: Session, admin_user: User):
        """Should return all keywords."""
        WatchlistService.add_keyword(db_session, "first", admin_user.id)
        WatchlistService.add_keyword(db_session, "second", admin_user.id)

        result = WatchlistService.get_all_keywords(db_session)

        assert len(result) == 2
        keywords = [k.keyword for k in result]
        assert "first" in keywords
        assert "second" in keywords

    def test_get_active_only(self, db_session: Session, admin_user: User):
        """Should filter to active keywords only."""
        WatchlistService.add_keyword(db_session, "active", admin_user.id)
        inactive = WatchlistService.add_keyword(db_session, "inactive", admin_user.id)
        WatchlistService.update_keyword(db_session, inactive.id, is_active=False)

        result = WatchlistService.get_all_keywords(db_session, active_only=True)

        assert len(result) == 1
        assert result[0].keyword == "active"

    def test_get_all_keywords_with_pagination(
        self, db_session: Session, admin_user: User
    ):
        """Should support pagination."""
        for i in range(5):
            WatchlistService.add_keyword(db_session, f"keyword{i}", admin_user.id)

        result = WatchlistService.get_all_keywords(db_session, skip=2, limit=2)

        assert len(result) == 2

    def test_get_all_keywords_ordered_by_match_count(
        self, db_session: Session, admin_user: User
    ):
        """Should order by match_count descending."""
        kw1 = WatchlistService.add_keyword(db_session, "low", admin_user.id)
        kw2 = WatchlistService.add_keyword(db_session, "high", admin_user.id)

        # Manually set match counts
        kw1.match_count = 5
        kw2.match_count = 100
        db_session.commit()

        result = WatchlistService.get_all_keywords(db_session)

        assert result[0].keyword == "high"
        assert result[1].keyword == "low"


class TestCheckContentForKeywords:
    """Tests for WatchlistService.check_content_for_keywords."""

    def test_check_content_no_match(
        self, db_session: Session, admin_user: User, test_idea: Idea
    ):
        """Should return empty list when no keywords match."""
        WatchlistService.add_keyword(db_session, "nomatch", admin_user.id)

        result = WatchlistService.check_content_for_keywords(
            db_session,
            "This is clean content",
            ContentType.IDEA,
            test_idea.id,
        )

        assert result == []

    def test_check_content_simple_match(
        self, db_session: Session, admin_user: User, test_idea: Idea
    ):
        """Should create flag for matching keyword."""
        WatchlistService.add_keyword(db_session, "spam", admin_user.id)

        result = WatchlistService.check_content_for_keywords(
            db_session,
            "This is spam content",
            ContentType.IDEA,
            test_idea.id,
        )

        assert len(result) == 1
        assert result[0].content_type == ContentType.IDEA
        assert result[0].content_id == test_idea.id
        assert result[0].reason == FlagReason.SPAM
        assert result[0].status == FlagStatus.PENDING
        assert result[0].details and "spam" in result[0].details

    def test_check_content_case_insensitive(
        self, db_session: Session, admin_user: User, test_idea: Idea
    ):
        """Should match case-insensitively."""
        WatchlistService.add_keyword(db_session, "SPAM", admin_user.id)

        result = WatchlistService.check_content_for_keywords(
            db_session,
            "This is spam content",
            ContentType.IDEA,
            test_idea.id,
        )

        assert len(result) == 1

    def test_check_content_regex_match(
        self, db_session: Session, admin_user: User, test_idea: Idea
    ):
        """Should match regex patterns."""
        WatchlistService.add_keyword(
            db_session, r"\bspam\b", admin_user.id, is_regex=True
        )

        result = WatchlistService.check_content_for_keywords(
            db_session,
            "This is spam content",
            ContentType.IDEA,
            test_idea.id,
        )

        assert len(result) == 1

    def test_check_content_regex_no_partial_match(
        self, db_session: Session, admin_user: User, test_idea: Idea
    ):
        """Should not match regex when boundary not met."""
        WatchlistService.add_keyword(
            db_session, r"\bspam\b", admin_user.id, is_regex=True
        )

        result = WatchlistService.check_content_for_keywords(
            db_session,
            "This is spammy content",  # 'spammy' should not match \bspam\b
            ContentType.IDEA,
            test_idea.id,
        )

        assert len(result) == 0

    def test_check_content_multiple_ideas(
        self, db_session: Session, admin_user: User, test_idea: Idea, test_category
    ):
        """Should create flags for same keyword matching different ideas."""
        # Create second idea
        idea2 = Idea(
            title="Second Idea",
            description="Another idea",
            category_id=test_category.id,
            user_id=admin_user.id,
        )
        db_session.add(idea2)
        db_session.commit()

        WatchlistService.add_keyword(db_session, "spam", admin_user.id)

        # Check first idea
        result1 = WatchlistService.check_content_for_keywords(
            db_session,
            "This is spam content",
            ContentType.IDEA,
            test_idea.id,
        )
        assert len(result1) == 1

        # Check second idea
        result2 = WatchlistService.check_content_for_keywords(
            db_session,
            "More spam here",
            ContentType.IDEA,
            idea2.id,
        )
        assert len(result2) == 1

    def test_check_content_inactive_keyword_ignored(
        self, db_session: Session, admin_user: User, test_idea: Idea
    ):
        """Should ignore inactive keywords."""
        keyword = WatchlistService.add_keyword(db_session, "inactive", admin_user.id)
        WatchlistService.update_keyword(db_session, keyword.id, is_active=False)

        result = WatchlistService.check_content_for_keywords(
            db_session,
            "This has inactive keyword",
            ContentType.IDEA,
            test_idea.id,
        )

        assert len(result) == 0

    def test_check_content_increments_match_count(
        self, db_session: Session, admin_user: User, test_idea: Idea
    ):
        """Should increment match_count for matched keyword."""
        keyword = WatchlistService.add_keyword(db_session, "counted", admin_user.id)
        assert keyword.match_count == 0

        WatchlistService.check_content_for_keywords(
            db_session,
            "This is counted content",
            ContentType.IDEA,
            test_idea.id,
        )

        db_session.refresh(keyword)
        assert keyword.match_count == 1

    def test_check_content_invalid_regex_skipped(
        self, db_session: Session, admin_user: User, test_idea: Idea
    ):
        """Should skip invalid regex patterns without error."""
        # Manually create invalid regex entry
        entry = KeywordWatchlist(
            keyword="[invalid",
            is_regex=True,
            auto_flag_reason=FlagReason.SPAM,
            is_active=True,
            created_by=admin_user.id,
        )
        db_session.add(entry)
        db_session.commit()

        # Should not raise, just skip invalid regex
        result = WatchlistService.check_content_for_keywords(
            db_session,
            "Any content here",
            ContentType.IDEA,
            test_idea.id,
        )

        assert len(result) == 0


class TestTestKeyword:
    """Tests for WatchlistService.test_keyword."""

    def test_simple_match(self):
        """Should return True for simple keyword match."""
        result = WatchlistService.test_keyword("test", "This is a test string")
        assert result is True

    def test_simple_no_match(self):
        """Should return False when keyword not in text."""
        result = WatchlistService.test_keyword("missing", "This is a test string")
        assert result is False

    def test_case_insensitive(self):
        """Should match case-insensitively."""
        result = WatchlistService.test_keyword("TEST", "this is a test string")
        assert result is True

    def test_regex_match(self):
        """Should match regex patterns."""
        result = WatchlistService.test_keyword(r"\d{3}-\d{4}", "Call 555-1234 now")
        assert result is True

    def test_regex_no_match(self):
        """Should return False for non-matching regex."""
        result = WatchlistService.test_keyword(r"\d{3}-\d{4}", "No phone here")
        assert result is False

    def test_invalid_regex_falls_back_to_plain(self):
        """Should fall back to plain text match for invalid regex."""
        # '[invalid' is invalid regex but valid as plain text
        result = WatchlistService.test_keyword("[invalid", "Contains [invalid text")
        assert result is True

    def test_word_boundary_regex(self):
        """Should respect word boundary in regex."""
        result = WatchlistService.test_keyword(r"\btest\b", "This is a test!")
        assert result is True

        result = WatchlistService.test_keyword(r"\btest\b", "This is testing")
        assert result is False
