"""Tests for CommentRepository."""

import repositories.db_models as db_models
from repositories.comment_repository import CommentRepository


class TestCommentRepository:
    """Test cases for CommentRepository."""

    def test_get_comments_for_idea_exclude_moderated(
        self, db_session, test_user, test_idea
    ):
        """Get comments for idea excludes moderated comments by default."""
        # Create comments
        comment1 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This is a normal comment",
            is_moderated=False,
        )
        comment2 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This is a moderated comment",
            is_moderated=True,
        )
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        repo = CommentRepository(db_session)
        results = repo.get_comments_for_idea(test_idea.id, include_moderated=False)

        # Should only return non-moderated comment
        assert len(results) == 1
        comment, username, display_name = results[0]
        assert comment.is_moderated is False
        assert username == test_user.username
        assert display_name == test_user.display_name

    def test_get_comments_for_idea_include_moderated(
        self, db_session, test_user, test_idea
    ):
        """Get comments for idea includes moderated when requested."""
        # Create comments
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

        repo = CommentRepository(db_session)
        results = repo.get_comments_for_idea(test_idea.id, include_moderated=True)

        # Should return both comments
        assert len(results) == 2

    def test_get_comments_for_idea_pagination(self, db_session, test_user, test_idea):
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

        repo = CommentRepository(db_session)

        # Test pagination
        page1 = repo.get_comments_for_idea(test_idea.id, skip=0, limit=2)
        page2 = repo.get_comments_for_idea(test_idea.id, skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2

    def test_get_by_user(self, db_session, test_user, test_idea):
        """Get comments by user."""
        # Create comments
        comment1 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="User comment 1",
            is_moderated=False,
        )
        comment2 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="User comment 2",
            is_moderated=False,
        )
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        repo = CommentRepository(db_session)
        comments = repo.get_by_user(test_user.id)

        assert len(comments) == 2
        assert all(c.user_id == test_user.id for c in comments)

    def test_get_by_user_pagination(self, db_session, test_user, test_idea):
        """Get comments by user with pagination."""
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

        repo = CommentRepository(db_session)

        # Test pagination
        page1 = repo.get_by_user(test_user.id, skip=0, limit=2)
        page2 = repo.get_by_user(test_user.id, skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2

    def test_get_all_comments(self, db_session, test_user, test_idea):
        """Get all comments including moderated."""
        # Create comments
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

        repo = CommentRepository(db_session)
        results = repo.get_all_comments()

        # Should return all comments
        assert len(results) == 2

    def test_get_all_comments_pagination(self, db_session, test_user, test_idea):
        """Get all comments with pagination."""
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

        repo = CommentRepository(db_session)

        # Test pagination
        page1 = repo.get_all_comments(skip=0, limit=2)
        page2 = repo.get_all_comments(skip=2, limit=2)

        assert len(page1) == 2
        assert len(page2) == 2

    def test_moderate_comment_success(self, db_session, test_user, test_idea):
        """Moderate a comment successfully."""
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

        repo = CommentRepository(db_session)
        updated = repo.moderate_comment(comment_id, True)

        assert updated is not None
        assert updated.is_moderated is True

    def test_moderate_comment_not_found(self, db_session):
        """Moderate non-existent comment returns None."""
        repo = CommentRepository(db_session)
        result = repo.moderate_comment(99999, True)
        assert result is None

    def test_get_comments_for_idea_excludes_soft_deleted(
        self, db_session, test_user, test_idea
    ):
        """Get comments for idea excludes soft-deleted comments."""
        from datetime import datetime, timezone

        # Create normal comment
        comment1 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This is a normal comment",
            is_moderated=False,
        )
        # Create soft-deleted comment (moderation actioned)
        comment2 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This comment was deleted by moderation",
            is_moderated=False,
            deleted_at=datetime.now(timezone.utc),
            deleted_by=test_user.id,
            deletion_reason="Removed by moderator: Content violation",
        )
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        repo = CommentRepository(db_session)
        results = repo.get_comments_for_idea(test_idea.id)

        # Should only return non-deleted comment
        assert len(results) == 1
        comment, username, display_name = results[0]
        assert comment.content == "This is a normal comment"
        assert comment.deleted_at is None

    def test_get_comments_for_idea_excludes_hidden(
        self, db_session, test_user, test_idea
    ):
        """Get comments for idea excludes hidden (flagged) comments."""
        from datetime import datetime, timezone

        # Create normal comment
        comment1 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This is a normal comment",
            is_moderated=False,
            is_hidden=False,
        )
        # Create hidden comment (flagged and pending review)
        comment2 = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This comment is hidden due to flags",
            is_moderated=False,
            is_hidden=True,
            hidden_at=datetime.now(timezone.utc),
            flag_count=3,
        )
        db_session.add(comment1)
        db_session.add(comment2)
        db_session.commit()

        repo = CommentRepository(db_session)
        results = repo.get_comments_for_idea(test_idea.id)

        # Should only return non-hidden comment
        assert len(results) == 1
        comment, username, display_name = results[0]
        assert comment.content == "This is a normal comment"
        assert comment.is_hidden is False

    def test_get_comments_for_idea_excludes_all_moderation_states(
        self, db_session, test_user, test_idea
    ):
        """Get comments excludes soft-deleted, hidden, and moderated comments."""
        from datetime import datetime, timezone

        # Create normal comment
        normal_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This is a normal visible comment",
            is_moderated=False,
            is_hidden=False,
        )
        # Create moderated comment
        moderated_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This comment is moderated",
            is_moderated=True,
        )
        # Create hidden comment
        hidden_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This comment is hidden",
            is_hidden=True,
            hidden_at=datetime.now(timezone.utc),
        )
        # Create soft-deleted comment
        deleted_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This comment is deleted",
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add(normal_comment)
        db_session.add(moderated_comment)
        db_session.add(hidden_comment)
        db_session.add(deleted_comment)
        db_session.commit()

        repo = CommentRepository(db_session)
        results = repo.get_comments_for_idea(test_idea.id)

        # Should only return the normal visible comment
        assert len(results) == 1
        comment, username, display_name = results[0]
        assert comment.content == "This is a normal visible comment"
