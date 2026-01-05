"""Tests for CommentLikeService."""

import pytest

import repositories.db_models as db_models
from models.exceptions import BusinessRuleException, CommentNotFoundException
from services.comment_like_service import CommentLikeService


@pytest.fixture
def test_comment(db_session, test_idea, other_user) -> db_models.Comment:
    """Create a test comment (by other_user, so test_user can like it)."""
    comment = db_models.Comment(
        idea_id=test_idea.id,
        user_id=other_user.id,
        content="This is a test comment",
        is_moderated=False,
        like_count=0,
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


@pytest.fixture
def test_user_comment(db_session, test_idea, test_user) -> db_models.Comment:
    """Create a test comment by test_user (user cannot like their own comment)."""
    comment = db_models.Comment(
        idea_id=test_idea.id,
        user_id=test_user.id,
        content="This is test user's comment",
        is_moderated=False,
        like_count=0,
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


@pytest.fixture
def deleted_comment(db_session, test_idea, other_user) -> db_models.Comment:
    """Create a deleted comment."""
    from datetime import datetime, timezone

    comment = db_models.Comment(
        idea_id=test_idea.id,
        user_id=other_user.id,
        content="This is a deleted comment",
        is_moderated=False,
        like_count=0,
        deleted_at=datetime.now(timezone.utc),
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


@pytest.fixture
def hidden_comment(db_session, test_idea, other_user) -> db_models.Comment:
    """Create a hidden comment."""
    comment = db_models.Comment(
        idea_id=test_idea.id,
        user_id=other_user.id,
        content="This is a hidden comment",
        is_moderated=False,
        is_hidden=True,
        like_count=0,
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


class TestToggleLike:
    """Tests for toggle_like method."""

    def test_like_comment_success(self, db_session, test_user, test_comment) -> None:
        """User can like another user's comment."""
        result = CommentLikeService.toggle_like(
            db_session, test_comment.id, test_user.id
        )
        assert result["liked"] is True
        assert result["like_count"] == 1

    def test_unlike_comment_success(self, db_session, test_user, test_comment) -> None:
        """User can unlike a previously liked comment."""
        # First like
        CommentLikeService.toggle_like(db_session, test_comment.id, test_user.id)
        # Then unlike
        result = CommentLikeService.toggle_like(
            db_session, test_comment.id, test_user.id
        )
        assert result["liked"] is False
        assert result["like_count"] == 0

    def test_toggle_multiple_times(self, db_session, test_user, test_comment) -> None:
        """User can toggle like multiple times."""
        # Like
        result1 = CommentLikeService.toggle_like(
            db_session, test_comment.id, test_user.id
        )
        assert result1["liked"] is True
        assert result1["like_count"] == 1

        # Unlike
        result2 = CommentLikeService.toggle_like(
            db_session, test_comment.id, test_user.id
        )
        assert result2["liked"] is False
        assert result2["like_count"] == 0

        # Like again
        result3 = CommentLikeService.toggle_like(
            db_session, test_comment.id, test_user.id
        )
        assert result3["liked"] is True
        assert result3["like_count"] == 1

    def test_cannot_like_own_comment(
        self, db_session, test_user, test_user_comment
    ) -> None:
        """User cannot like their own comment."""
        with pytest.raises(BusinessRuleException, match="own comment"):
            CommentLikeService.toggle_like(
                db_session, test_user_comment.id, test_user.id
            )

    def test_cannot_like_deleted_comment(
        self, db_session, test_user, deleted_comment
    ) -> None:
        """Cannot like a deleted comment."""
        with pytest.raises(BusinessRuleException, match="deleted"):
            CommentLikeService.toggle_like(db_session, deleted_comment.id, test_user.id)

    def test_cannot_like_hidden_comment(
        self, db_session, test_user, hidden_comment
    ) -> None:
        """Cannot like a hidden comment."""
        with pytest.raises(BusinessRuleException, match="hidden"):
            CommentLikeService.toggle_like(db_session, hidden_comment.id, test_user.id)

    def test_comment_not_found(self, db_session, test_user) -> None:
        """Raises CommentNotFoundException for non-existent comment."""
        with pytest.raises(CommentNotFoundException):
            CommentLikeService.toggle_like(db_session, 99999, test_user.id)

    def test_multiple_users_like(
        self, db_session, test_user, other_user, admin_user, test_user_comment
    ) -> None:
        """Multiple users can like the same comment."""
        # other_user likes test_user's comment
        result1 = CommentLikeService.toggle_like(
            db_session, test_user_comment.id, other_user.id
        )
        assert result1["liked"] is True
        assert result1["like_count"] == 1

        # admin_user also likes test_user's comment
        result2 = CommentLikeService.toggle_like(
            db_session, test_user_comment.id, admin_user.id
        )
        assert result2["liked"] is True
        assert result2["like_count"] == 2

        # other_user unlikes
        result3 = CommentLikeService.toggle_like(
            db_session, test_user_comment.id, other_user.id
        )
        assert result3["liked"] is False
        assert result3["like_count"] == 1


class TestGetUserLikedStatus:
    """Tests for get_user_liked_status method."""

    def test_returns_empty_for_none_user(self, db_session, test_comment) -> None:
        """Returns empty dict when user_id is None."""
        result = CommentLikeService.get_user_liked_status(
            db_session, [test_comment.id], None
        )
        assert result == {}

    def test_returns_empty_for_empty_comment_ids(self, db_session, test_user) -> None:
        """Returns empty dict when comment_ids is empty."""
        result = CommentLikeService.get_user_liked_status(db_session, [], test_user.id)
        assert result == {}

    def test_returns_correct_status(
        self, db_session, test_user, test_comment, test_user_comment
    ) -> None:
        """Returns correct like status for multiple comments."""
        # Like one comment
        CommentLikeService.toggle_like(db_session, test_comment.id, test_user.id)

        # Check status for both comments
        result = CommentLikeService.get_user_liked_status(
            db_session, [test_comment.id, test_user_comment.id], test_user.id
        )

        assert result[test_comment.id] is True
        assert result[test_user_comment.id] is False

    def test_returns_all_false_when_no_likes(
        self, db_session, test_user, test_comment, test_user_comment
    ) -> None:
        """Returns all False when user hasn't liked any comments."""
        result = CommentLikeService.get_user_liked_status(
            db_session, [test_comment.id, test_user_comment.id], test_user.id
        )

        assert result[test_comment.id] is False
        assert result[test_user_comment.id] is False
