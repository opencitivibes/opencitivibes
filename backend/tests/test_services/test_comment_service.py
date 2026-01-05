"""Tests for CommentService."""

import pytest
import repositories.db_models as db_models
from models.exceptions import (
    IdeaNotFoundException,
    BusinessRuleException,
    CommentNotFoundException,
    InsufficientPermissionsException,
)
from services.comment_service import CommentService


class TestCommentService:
    """Test cases for CommentService."""

    def test_get_comments_for_idea_success(self, db_session, test_user, test_idea):
        """Get comments for approved idea."""
        # Create comment
        comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Test comment",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()

        result = CommentService.get_comments_for_idea(db_session, test_idea.id)

        assert len(result) == 1
        assert result[0].content == "Test comment"
        assert result[0].author_username == test_user.username

    def test_get_comments_for_idea_not_found(self, db_session):
        """Get comments raises exception for non-existent idea."""
        with pytest.raises(IdeaNotFoundException):
            CommentService.get_comments_for_idea(db_session, 99999)

    def test_get_comments_for_idea_not_approved(self, db_session, pending_idea):
        """Get comments raises exception for non-approved idea."""
        with pytest.raises(BusinessRuleException):
            CommentService.get_comments_for_idea(db_session, pending_idea.id)

    def test_get_comments_for_idea_excludes_moderated(
        self, db_session, test_user, test_idea
    ):
        """Get comments excludes moderated comments."""
        # Create normal and moderated comments
        comment1 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Normal comment",
            is_moderated=False,
        )
        comment2 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Moderated comment",
            is_moderated=True,
        )
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        result = CommentService.get_comments_for_idea(db_session, test_idea.id)

        assert len(result) == 1
        assert result[0].content == "Normal comment"

    def test_get_comments_for_idea_excludes_soft_deleted(
        self, db_session, test_user, test_idea
    ):
        """Get comments excludes soft-deleted (moderation actioned) comments."""
        from datetime import datetime, timezone

        # Create normal comment
        comment1 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Normal comment",
            is_moderated=False,
        )
        # Create soft-deleted comment (from moderation action)
        comment2 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Deleted comment",
            is_moderated=False,
            deleted_at=datetime.now(timezone.utc),
            deleted_by=test_user.id,
            deletion_reason="Removed by moderator",
        )
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        result = CommentService.get_comments_for_idea(db_session, test_idea.id)

        assert len(result) == 1
        assert result[0].content == "Normal comment"

    def test_get_comments_for_idea_excludes_hidden(
        self, db_session, test_user, test_idea
    ):
        """Get comments excludes hidden (flagged) comments."""
        from datetime import datetime, timezone

        # Create normal comment
        comment1 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Normal comment",
            is_moderated=False,
            is_hidden=False,
        )
        # Create hidden comment (flagged and auto-hidden)
        comment2 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Hidden flagged comment",
            is_moderated=False,
            is_hidden=True,
            hidden_at=datetime.now(timezone.utc),
            flag_count=3,
        )
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        result = CommentService.get_comments_for_idea(db_session, test_idea.id)

        assert len(result) == 1
        assert result[0].content == "Normal comment"

    def test_create_comment_success(self, db_session, test_user, test_idea):
        """Create comment on approved idea."""
        result, requires_approval = CommentService.create_comment(
            db=db_session,
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="New comment",
            username=test_user.username,
            display_name=test_user.display_name,
        )

        assert result is not None
        assert result.content == "New comment"
        assert result.author_username == test_user.username
        # Note: is_moderated may be True if user requires approval
        assert isinstance(requires_approval, bool)

    def test_create_comment_idea_not_found(self, db_session, test_user):
        """Create comment raises exception for non-existent idea."""
        with pytest.raises(IdeaNotFoundException):
            CommentService.create_comment(
                db=db_session,
                idea_id=99999,
                user_id=test_user.id,
                content="Comment",
                username=test_user.username,
                display_name=test_user.display_name,
            )

    def test_create_comment_idea_not_approved(
        self, db_session, test_user, pending_idea
    ):
        """Create comment raises exception for non-approved idea."""
        with pytest.raises(BusinessRuleException):
            CommentService.create_comment(
                db=db_session,
                idea_id=pending_idea.id,
                user_id=test_user.id,
                content="Comment",
                username=test_user.username,
                display_name=test_user.display_name,
            )

    def test_delete_comment_success(self, db_session, test_user, test_idea):
        """Delete own comment successfully."""
        # Create comment
        comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Comment to delete",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        comment_id = comment.id

        CommentService.delete_comment(db_session, comment_id, test_user.id)

        # Verify comment is deleted
        deleted = db_session.query(db_models.Comment).filter_by(id=comment_id).first()
        assert deleted is None

    def test_delete_comment_not_found(self, db_session, test_user):
        """Delete non-existent comment raises exception."""
        with pytest.raises(CommentNotFoundException):
            CommentService.delete_comment(db_session, 99999, test_user.id)

    def test_delete_comment_not_author(
        self, db_session, test_user, other_user, test_idea
    ):
        """Delete comment by non-author raises exception."""
        # Create comment by test_user
        comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Comment by test user",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()

        # Try to delete as other_user
        with pytest.raises(InsufficientPermissionsException):
            CommentService.delete_comment(db_session, comment.id, other_user.id)

    def test_get_all_comments(self, db_session, test_user, test_idea):
        """Get all comments including moderated (admin function)."""
        # Create normal and moderated comments
        comment1 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Normal comment",
            is_moderated=False,
        )
        comment2 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Moderated comment",
            is_moderated=True,
        )
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        result = CommentService.get_all_comments(db_session)

        # Should include both comments
        assert len(result) >= 2
        contents = [c.content for c in result]
        assert "Normal comment" in contents
        assert "Moderated comment" in contents

    def test_moderate_comment_success(self, db_session, test_user, test_idea):
        """Moderate comment successfully."""
        # Create comment
        comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Comment to moderate",
            is_moderated=False,
        )
        db_session.add(comment)
        db_session.commit()
        comment_id = comment.id

        result = CommentService.moderate_comment(db_session, comment_id, True)

        assert result is not None
        assert result.is_moderated is True

    def test_moderate_comment_not_found(self, db_session):
        """Moderate non-existent comment raises exception."""
        with pytest.raises(CommentNotFoundException):
            CommentService.moderate_comment(db_session, 99999, True)

    def test_get_comments_pagination(self, db_session, test_user, test_idea):
        """Get comments with pagination."""
        # Create multiple comments
        for i in range(5):
            comment = db_models.Comment(
                idea_id=test_idea.id,
                user_id=test_user.id,
                content=f"Comment {i}",
                is_moderated=False,
            )
            db_session.add(comment)
        db_session.commit()

        # Test pagination
        page1 = CommentService.get_comments_for_idea(
            db_session, test_idea.id, skip=0, limit=2
        )
        page2 = CommentService.get_comments_for_idea(
            db_session, test_idea.id, skip=2, limit=2
        )

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id
