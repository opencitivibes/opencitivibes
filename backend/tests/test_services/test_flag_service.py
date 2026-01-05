"""
Unit tests for FlagService.
"""

import pytest

from models.exceptions import (
    CannotFlagOwnContentException,
    CommentNotFoundException,
    DuplicateFlagException,
    FlagAlreadyReviewedException,
    FlagNotFoundException,
)
from repositories.db_models import (
    Comment,
    ContentType,
    FlagReason,
    FlagStatus,
)
from services.flag_service import FLAG_THRESHOLD, FlagService


class TestFlagServiceCreateFlag:
    """Tests for FlagService.create_flag"""

    def test_create_flag_success_on_comment(
        self, db_session, test_user, other_user, test_idea
    ):
        """Test successful flag creation on a comment."""
        # Create a comment by test_user
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # other_user flags the comment
        flag = FlagService.create_flag(
            db=db_session,
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            details="This is spam",
        )

        assert flag is not None
        assert flag.content_type == ContentType.COMMENT
        assert flag.content_id == comment.id
        assert flag.reporter_id == other_user.id
        assert flag.reason == FlagReason.SPAM
        assert flag.status == FlagStatus.PENDING

    def test_create_flag_success_on_idea(
        self, db_session, test_user, other_user, test_category
    ):
        """Test successful flag creation on an idea."""
        from repositories.db_models import Idea, IdeaStatus

        # Create an idea by test_user
        idea = Idea(
            title="Test Idea for Flagging",
            description="A test idea description",
            category_id=test_category.id,
            user_id=test_user.id,
            status=IdeaStatus.APPROVED,
        )
        db_session.add(idea)
        db_session.commit()
        db_session.refresh(idea)

        # other_user flags the idea
        flag = FlagService.create_flag(
            db=db_session,
            content_type=ContentType.IDEA,
            content_id=idea.id,
            reporter_id=other_user.id,
            reason=FlagReason.HARASSMENT,
            details="Inappropriate content",
        )

        assert flag is not None
        assert flag.content_type == ContentType.IDEA
        assert flag.content_id == idea.id
        assert flag.reason == FlagReason.HARASSMENT

    def test_create_flag_own_content_fails(self, db_session, test_user, test_idea):
        """Test that users cannot flag their own content."""
        # Create a comment by test_user
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="My own comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # test_user tries to flag their own comment
        with pytest.raises(CannotFlagOwnContentException):
            FlagService.create_flag(
                db=db_session,
                content_type=ContentType.COMMENT,
                content_id=comment.id,
                reporter_id=test_user.id,
                reason=FlagReason.SPAM,
            )

    def test_create_flag_duplicate_fails(
        self, db_session, test_user, other_user, test_idea
    ):
        """Test that duplicate flags are rejected."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # First flag succeeds
        FlagService.create_flag(
            db=db_session,
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
        )

        # Second flag from same user fails
        with pytest.raises(DuplicateFlagException):
            FlagService.create_flag(
                db=db_session,
                content_type=ContentType.COMMENT,
                content_id=comment.id,
                reporter_id=other_user.id,
                reason=FlagReason.HARASSMENT,  # Different reason, still fails
            )

    def test_create_flag_nonexistent_content_fails(self, db_session, test_user):
        """Test that flagging nonexistent content fails."""
        with pytest.raises(CommentNotFoundException):
            FlagService.create_flag(
                db=db_session,
                content_type=ContentType.COMMENT,
                content_id=99999,
                reporter_id=test_user.id,
                reason=FlagReason.SPAM,
            )


class TestFlagServiceRetractFlag:
    """Tests for FlagService.retract_flag"""

    def test_retract_flag_success(self, db_session, test_user, other_user, test_idea):
        """Test successful flag retraction."""
        # Create a comment and flag it
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        flag = FlagService.create_flag(
            db=db_session,
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
        )
        flag_id = flag.id

        # Retract the flag
        FlagService.retract_flag(
            db=db_session,
            flag_id=flag_id,
            user_id=other_user.id,
        )

        # Flag should be deleted
        from repositories.flag_repository import FlagRepository

        flag_repo = FlagRepository(db_session)
        assert flag_repo.get_by_id(flag_id) is None

    def test_retract_flag_not_owner_fails(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test that non-owners cannot retract flags."""
        # Create a comment and flag it
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        flag = FlagService.create_flag(
            db=db_session,
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
        )

        # admin_user tries to retract other_user's flag
        with pytest.raises(FlagNotFoundException):
            FlagService.retract_flag(
                db=db_session,
                flag_id=flag.id,
                user_id=admin_user.id,
            )

    def test_retract_reviewed_flag_fails(
        self, db_session, test_user, other_user, test_idea
    ):
        """Test that reviewed flags cannot be retracted."""
        # Create a comment and flag it
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        flag = FlagService.create_flag(
            db=db_session,
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
        )

        # Mark flag as reviewed
        flag.status = FlagStatus.ACTIONED  # type: ignore[assignment]
        db_session.commit()

        # Try to retract
        with pytest.raises(FlagAlreadyReviewedException):
            FlagService.retract_flag(
                db=db_session,
                flag_id=flag.id,
                user_id=other_user.id,
            )


class TestFlagServiceAutoHide:
    """Tests for auto-hide functionality."""

    def test_content_hidden_at_threshold(self, db_session, test_user, test_idea):
        """Test that content is hidden after FLAG_THRESHOLD flags."""
        from authentication.auth import get_password_hash

        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment to be hidden",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create FLAG_THRESHOLD flags from different users
        from repositories.db_models import User

        for i in range(FLAG_THRESHOLD):
            reporter = User(
                email=f"reporter{i}@example.com",
                username=f"reporter{i}",
                display_name=f"Reporter {i}",
                hashed_password=get_password_hash("password123"),
                is_active=True,
                is_global_admin=False,
            )
            db_session.add(reporter)
            db_session.commit()
            db_session.refresh(reporter)

            FlagService.create_flag(
                db=db_session,
                content_type=ContentType.COMMENT,
                content_id=comment.id,
                reporter_id=reporter.id,
                reason=FlagReason.SPAM,
            )

        # Refresh comment
        db_session.refresh(comment)

        assert comment.is_hidden is True
        assert comment.hidden_at is not None
        assert comment.flag_count == FLAG_THRESHOLD

    def test_content_not_hidden_below_threshold(self, db_session, test_user, test_idea):
        """Test that content is not hidden below threshold."""
        from authentication.auth import get_password_hash
        from repositories.db_models import User

        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment below threshold",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create fewer flags than threshold
        for i in range(FLAG_THRESHOLD - 1):
            reporter = User(
                email=f"reporter{i}@example.com",
                username=f"reporter{i}",
                display_name=f"Reporter {i}",
                hashed_password=get_password_hash("password123"),
                is_active=True,
                is_global_admin=False,
            )
            db_session.add(reporter)
            db_session.commit()
            db_session.refresh(reporter)

            FlagService.create_flag(
                db=db_session,
                content_type=ContentType.COMMENT,
                content_id=comment.id,
                reporter_id=reporter.id,
                reason=FlagReason.SPAM,
            )

        db_session.refresh(comment)

        assert comment.is_hidden is False
        assert comment.flag_count == FLAG_THRESHOLD - 1


class TestFlagServiceGetFlags:
    """Tests for FlagService flag retrieval methods."""

    def test_get_user_flags(self, db_session, test_user, other_user, test_idea):
        """Test getting flags submitted by a user."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # other_user creates a flag
        FlagService.create_flag(
            db=db_session,
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
        )

        # Get flags for other_user
        flags = FlagService.get_user_flags(db=db_session, user_id=other_user.id)

        assert len(flags) == 1
        assert flags[0].reporter_id == other_user.id

    def test_check_user_already_flagged_true(
        self, db_session, test_user, other_user, test_idea
    ):
        """Test check_user_already_flagged returns True when flagged."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # other_user flags it
        FlagService.create_flag(
            db=db_session,
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
        )

        # Check
        result = FlagService.check_user_already_flagged(
            db=db_session,
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            user_id=other_user.id,
        )
        assert result is True

    def test_check_user_already_flagged_false(self, db_session, test_user, test_idea):
        """Test check_user_already_flagged returns False when not flagged."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Check without flagging (test_user is author so can't flag anyway)
        from authentication.auth import get_password_hash
        from repositories.db_models import User

        checker = User(
            email="checker@example.com",
            username="checker",
            display_name="Checker",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_global_admin=False,
        )
        db_session.add(checker)
        db_session.commit()
        db_session.refresh(checker)

        result = FlagService.check_user_already_flagged(
            db=db_session,
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            user_id=checker.id,
        )
        assert result is False
