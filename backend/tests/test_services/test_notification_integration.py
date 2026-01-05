"""Integration tests for notification triggering in IdeaService and CommentService."""

from unittest.mock import patch

import pytest

import models.schemas as schemas
import repositories.db_models as db_models
from services.comment_service import CommentService
from services.idea_service import IdeaService


class TestIdeaCreationNotification:
    """Test that idea creation triggers notifications."""

    def test_create_idea_triggers_notification(
        self,
        db_session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ) -> None:
        """Creating an idea should trigger admin notification."""
        with patch("services.notification_service.NotificationService") as mock_notif:
            idea_data = schemas.IdeaCreate(
                title="Test Notification Idea",
                description="This should trigger a notification to admins for review.",
                category_id=int(test_category.id),
                tags=[],
            )

            idea = IdeaService.validate_and_create_idea(
                db_session, idea_data, int(test_user.id)
            )

            # Verify notification was triggered
            mock_notif.notify_new_idea.assert_called_once()

            # Verify correct arguments
            call_kwargs = mock_notif.notify_new_idea.call_args.kwargs
            assert call_kwargs["idea_id"] == idea.id
            assert call_kwargs["title"] == "Test Notification Idea"
            assert call_kwargs["category_name"] == test_category.name_en

    def test_notification_includes_author_display_name(
        self,
        db_session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ) -> None:
        """Notification should include the author's display name."""
        with patch("services.notification_service.NotificationService") as mock_notif:
            idea_data = schemas.IdeaCreate(
                title="Test Author Name",
                description="Testing that author name is included in notification",
                category_id=int(test_category.id),
                tags=[],
            )

            IdeaService.validate_and_create_idea(
                db_session, idea_data, int(test_user.id)
            )

            call_kwargs = mock_notif.notify_new_idea.call_args.kwargs
            assert call_kwargs["author_display_name"] == test_user.display_name

    def test_notification_called_after_idea_persisted(
        self,
        db_session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ) -> None:
        """Notification should be called with valid idea ID (after commit)."""
        with patch("services.notification_service.NotificationService") as mock_notif:
            idea_data = schemas.IdeaCreate(
                title="Persistence Test",
                description="Verify idea is persisted before notification is sent",
                category_id=int(test_category.id),
                tags=[],
            )

            idea = IdeaService.validate_and_create_idea(
                db_session, idea_data, int(test_user.id)
            )

            # Verify idea_id in notification matches created idea
            call_kwargs = mock_notif.notify_new_idea.call_args.kwargs
            assert call_kwargs["idea_id"] == idea.id
            assert idea.id is not None  # Ensure it was persisted


class TestCommentCreationNotification:
    """Test that comment creation triggers notifications when needed."""

    @pytest.fixture
    def approved_idea(
        self,
        db_session,
        test_user: db_models.User,
        test_category: db_models.Category,
    ) -> db_models.Idea:
        """Create an approved idea for comment testing."""
        idea = db_models.Idea(
            title="Approved Idea for Comments",
            description="This idea is approved and can receive comments.",
            category_id=int(test_category.id),
            user_id=int(test_user.id),
            status=db_models.IdeaStatus.APPROVED,
        )
        db_session.add(idea)
        db_session.commit()
        db_session.refresh(idea)
        return idea

    def test_comment_requiring_approval_triggers_notification(
        self,
        db_session,
        approved_idea: db_models.Idea,
        test_user: db_models.User,
    ) -> None:
        """Comment requiring approval should trigger admin notification."""
        with patch("services.notification_service.NotificationService") as mock_notif:
            # Mock TrustScoreService at source to require approval
            with patch("services.trust_score_service.TrustScoreService") as mock_trust:
                mock_trust.requires_comment_approval.return_value = True

                comment, requires_approval = CommentService.create_comment(
                    db=db_session,
                    idea_id=int(approved_idea.id),
                    user_id=int(test_user.id),
                    content="This comment needs approval",
                    username=str(test_user.username),
                    display_name=str(test_user.display_name),
                )

                assert requires_approval is True
                # Verify notification was triggered
                mock_notif.notify_new_comment.assert_called_once()

                call_kwargs = mock_notif.notify_new_comment.call_args.kwargs
                assert call_kwargs["comment_id"] == comment.id
                assert call_kwargs["idea_title"] == approved_idea.title
                assert call_kwargs["author_display_name"] == test_user.display_name

    def test_trusted_user_comment_no_notification(
        self,
        db_session,
        approved_idea: db_models.Idea,
        test_user: db_models.User,
    ) -> None:
        """Comment from trusted user should NOT trigger notification."""
        with patch("services.notification_service.NotificationService") as mock_notif:
            # Mock TrustScoreService to NOT require approval (trusted user)
            with patch("services.trust_score_service.TrustScoreService") as mock_trust:
                mock_trust.requires_comment_approval.return_value = False

                comment, requires_approval = CommentService.create_comment(
                    db=db_session,
                    idea_id=int(approved_idea.id),
                    user_id=int(test_user.id),
                    content="This comment is from a trusted user",
                    username=str(test_user.username),
                    display_name=str(test_user.display_name),
                )

                assert requires_approval is False
                # Should NOT trigger notification for trusted users
                mock_notif.notify_new_comment.assert_not_called()
