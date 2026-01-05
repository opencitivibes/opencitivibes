"""
Unit tests for ModerationService.
"""

import pytest

from authentication.auth import get_password_hash
from models.exceptions import FlagNotFoundException
from repositories.db_models import (
    Comment,
    ContentFlag,
    ContentType,
    FlagReason,
    FlagStatus,
    Idea,
    IdeaStatus,
    PenaltyType,
    User,
)
from services.moderation_service import ModerationService


class TestModerationServiceGetModerationQueue:
    """Tests for ModerationService.get_moderation_queue"""

    def test_get_moderation_queue_empty(self, db_session):
        """Test getting moderation queue when there are no flags."""
        result, total, pending = ModerationService.get_moderation_queue(db_session)

        assert result == []
        assert total == 0
        assert pending == 0

    def test_get_moderation_queue_with_flags(
        self, db_session, test_user, other_user, test_idea
    ):
        """Test getting moderation queue with pending flags."""
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

        # Create flags
        flag1 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag1)

        # Create another user and another flag
        reporter2 = User(
            email="reporter2@example.com",
            username="reporter2",
            display_name="Reporter 2",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_global_admin=False,
        )
        db_session.add(reporter2)
        db_session.commit()
        db_session.refresh(reporter2)

        flag2 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=reporter2.id,
            reason=FlagReason.HARASSMENT,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag2)
        db_session.commit()

        result, total, pending = ModerationService.get_moderation_queue(db_session)

        assert len(result) == 1  # One unique content item
        assert total == 1
        assert pending == 2  # Two pending flags total
        assert result[0]["content_type"] == ContentType.COMMENT
        assert result[0]["content_id"] == comment.id
        assert result[0]["flag_count"] == 2
        assert len(result[0]["flags"]) == 2

    def test_get_moderation_queue_filter_by_content_type(
        self, db_session, test_user, other_user, test_idea, test_category
    ):
        """Test filtering moderation queue by content type."""
        # Create a comment with flag
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        flag1 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag1)

        # Create an idea with flag
        idea = Idea(
            title="Test Idea for Flag",
            description="A test idea description",
            category_id=test_category.id,
            user_id=test_user.id,
            status=IdeaStatus.APPROVED,
        )
        db_session.add(idea)
        db_session.commit()
        db_session.refresh(idea)

        flag2 = ContentFlag(
            content_type=ContentType.IDEA,
            content_id=idea.id,
            reporter_id=other_user.id,
            reason=FlagReason.HATE_SPEECH,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag2)
        db_session.commit()

        # Filter by COMMENT only
        result, total, pending = ModerationService.get_moderation_queue(
            db_session, content_type=ContentType.COMMENT
        )

        assert len(result) == 1
        assert result[0]["content_type"] == ContentType.COMMENT
        assert total == 1

        # Filter by IDEA only
        result, total, pending = ModerationService.get_moderation_queue(
            db_session, content_type=ContentType.IDEA
        )

        assert len(result) == 1
        assert result[0]["content_type"] == ContentType.IDEA
        assert total == 1

    def test_get_moderation_queue_filter_by_reason(
        self, db_session, test_user, other_user, test_idea
    ):
        """Test filtering moderation queue by flag reason."""
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

        # Create spam flag
        flag1 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag1)
        db_session.commit()

        # Filter by SPAM
        result, total, pending = ModerationService.get_moderation_queue(
            db_session, reason=FlagReason.SPAM
        )

        assert len(result) == 1
        assert result[0]["flags"][0]["reason"] == FlagReason.SPAM

        # Filter by HARASSMENT (should get nothing)
        result, total, pending = ModerationService.get_moderation_queue(
            db_session, reason=FlagReason.HARASSMENT
        )

        assert len(result) == 0
        assert total == 0


class TestModerationServiceReviewFlags:
    """Tests for ModerationService.review_flags"""

    def test_review_flags_dismiss(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test dismissing flags."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
            is_hidden=True,  # Auto-hidden by flags
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create flag
        flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag)
        db_session.commit()
        db_session.refresh(flag)

        # Dismiss the flag
        result = ModerationService.review_flags(
            db=db_session,
            flag_ids=[flag.id],
            action="dismiss",
            reviewer_id=admin_user.id,
            review_notes="False report",
        )

        assert result["action"] == "dismissed"
        assert result["flags_updated"] == 1
        assert result["content_unhidden"] is True

        # Check flag status
        db_session.refresh(flag)
        assert flag.status == FlagStatus.DISMISSED
        assert flag.reviewed_by == admin_user.id
        assert flag.review_notes == "False report"

        # Check content is unhidden
        db_session.refresh(comment)
        assert comment.is_hidden is False
        assert comment.flag_count == 0

    def test_review_flags_action(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test actioning flags (deleting content)."""
        # Create a comment
        comment = Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment to delete",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        # Create flag
        flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag)
        db_session.commit()
        db_session.refresh(flag)

        # Action the flag
        result = ModerationService.review_flags(
            db=db_session,
            flag_ids=[flag.id],
            action="action",
            reviewer_id=admin_user.id,
            review_notes="Confirmed spam",
        )

        assert result["action"] == "actioned"
        assert result["flags_updated"] == 1
        assert result["content_deleted"] is True
        assert result["penalty_issued"] is None

        # Check flag status
        db_session.refresh(flag)
        assert flag.status == FlagStatus.ACTIONED

        # Check content is deleted
        db_session.refresh(comment)
        assert comment.deleted_at is not None
        assert comment.deleted_by == admin_user.id
        assert "moderator" in (comment.deletion_reason or "")

    def test_review_flags_with_penalty(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test actioning flags with penalty."""
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

        # Create flag
        flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.HARASSMENT,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag)
        db_session.commit()
        db_session.refresh(flag)

        # Action with penalty
        result = ModerationService.review_flags(
            db=db_session,
            flag_ids=[flag.id],
            action="action",
            reviewer_id=admin_user.id,
            review_notes="Harassment confirmed",
            issue_penalty=True,
            penalty_type=PenaltyType.WARNING,
            penalty_reason="Harassment violation",
        )

        assert result["action"] == "actioned"
        assert result["penalty_issued"] is not None

        # Verify penalty was created
        from repositories.penalty_repository import PenaltyRepository

        penalty_repo = PenaltyRepository(db_session)
        penalty = penalty_repo.get_by_id(result["penalty_issued"])
        assert penalty is not None
        assert penalty.user_id == test_user.id
        assert penalty.penalty_type == PenaltyType.WARNING

    def test_review_flags_not_found(self, db_session, admin_user):
        """Test reviewing non-existent flags fails."""
        with pytest.raises(FlagNotFoundException):
            ModerationService.review_flags(
                db=db_session,
                flag_ids=[99999],
                action="dismiss",
                reviewer_id=admin_user.id,
            )

    def test_review_flags_multiple_flags(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test reviewing multiple flags at once."""
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

        # Create multiple flags
        flag1 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag1)
        db_session.commit()
        db_session.refresh(flag1)

        reporter2 = User(
            email="reporter2@example.com",
            username="reporter2",
            display_name="Reporter 2",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            is_global_admin=False,
        )
        db_session.add(reporter2)
        db_session.commit()
        db_session.refresh(reporter2)

        flag2 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=reporter2.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag2)
        db_session.commit()
        db_session.refresh(flag2)

        # Review both flags
        result = ModerationService.review_flags(
            db=db_session,
            flag_ids=[flag1.id, flag2.id],
            action="dismiss",
            reviewer_id=admin_user.id,
        )

        assert result["flags_updated"] == 2

        # Both should be dismissed
        db_session.refresh(flag1)
        db_session.refresh(flag2)
        assert flag1.status == FlagStatus.DISMISSED
        assert flag2.status == FlagStatus.DISMISSED


class TestModerationServiceGetFlaggedUsers:
    """Tests for ModerationService.get_flagged_users"""

    def test_get_flagged_users_empty(self, db_session):
        """Test getting flagged users when there are none."""
        users, total = ModerationService.get_flagged_users(db_session)

        assert users == []
        assert total == 0

    def test_get_flagged_users_with_pending(
        self, db_session, test_user, other_user, test_idea
    ):
        """Test getting flagged users with pending flags."""
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

        # Flag it
        flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag)
        db_session.commit()

        users, total = ModerationService.get_flagged_users(db_session)

        assert total == 1
        assert len(users) == 1
        assert users[0]["user_id"] == test_user.id
        assert users[0]["username"] == test_user.username
        assert users[0]["pending_flags_count"] == 1
        assert users[0]["has_active_penalty"] is False

    def test_get_flagged_users_with_penalty(
        self, db_session, test_user, other_user, admin_user, test_idea
    ):
        """Test flagged users display shows active penalties."""
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

        # Flag it
        flag = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag)
        db_session.commit()

        # Issue penalty to test_user
        from services.penalty_service import PenaltyService

        PenaltyService.issue_penalty(
            db=db_session,
            user_id=test_user.id,
            penalty_type=PenaltyType.TEMP_BAN_24H,
            reason="Test penalty",
            issued_by=admin_user.id,
        )

        users, total = ModerationService.get_flagged_users(db_session)

        assert len(users) == 1
        assert users[0]["has_active_penalty"] is True
        assert users[0]["active_penalty_type"] == PenaltyType.TEMP_BAN_24H

    def test_get_flagged_users_multiple_content(
        self, db_session, test_user, other_user, test_idea, test_category
    ):
        """Test user with multiple flagged content items."""
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

        # Flag comment
        flag1 = ContentFlag(
            content_type=ContentType.COMMENT,
            content_id=comment.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag1)

        # Create an idea
        idea = Idea(
            title="Test Idea",
            description="Test idea description",
            category_id=test_category.id,
            user_id=test_user.id,
            status=IdeaStatus.APPROVED,
        )
        db_session.add(idea)
        db_session.commit()
        db_session.refresh(idea)

        # Flag idea
        flag2 = ContentFlag(
            content_type=ContentType.IDEA,
            content_id=idea.id,
            reporter_id=other_user.id,
            reason=FlagReason.SPAM,
            status=FlagStatus.PENDING,
        )
        db_session.add(flag2)
        db_session.commit()

        users, total = ModerationService.get_flagged_users(db_session)

        assert len(users) == 1
        assert users[0]["pending_flags_count"] == 2  # Both flags counted

    def test_get_flagged_users_pagination(
        self, db_session, test_category, other_user, test_idea
    ):
        """Test pagination of flagged users."""
        # Create multiple users with flagged content
        for i in range(5):
            user = User(
                email=f"flagged{i}@example.com",
                username=f"flagged{i}",
                display_name=f"Flagged {i}",
                hashed_password=get_password_hash("password123"),
                is_active=True,
                is_global_admin=False,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create comment by this user
            comment = Comment(
                idea_id=test_idea.id,
                user_id=user.id,
                content=f"Comment {i}",
                is_moderated=False,
            )
            db_session.add(comment)
            db_session.commit()
            db_session.refresh(comment)

            # Flag it
            flag = ContentFlag(
                content_type=ContentType.COMMENT,
                content_id=comment.id,
                reporter_id=other_user.id,
                reason=FlagReason.SPAM,
                status=FlagStatus.PENDING,
            )
            db_session.add(flag)

        db_session.commit()

        # Get first page
        users, total = ModerationService.get_flagged_users(db_session, skip=0, limit=3)

        assert total == 5
        assert len(users) == 3

        # Get second page
        users, total = ModerationService.get_flagged_users(db_session, skip=3, limit=3)

        assert total == 5
        assert len(users) == 2
