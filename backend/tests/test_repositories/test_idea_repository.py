"""Tests for IdeaRepository comment count functionality."""

from datetime import datetime, timezone

import repositories.db_models as db_models
from repositories.idea_repository import IdeaRepository


class TestIdeaRepositoryCommentCount:
    """Test cases for comment count in leaderboard and idea queries."""

    def test_leaderboard_comment_count_excludes_deleted_comments(
        self, db_session, test_user, test_idea
    ):
        """Comment count in leaderboard excludes soft-deleted comments."""
        # Create a visible comment
        visible_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This is a visible comment",
            is_moderated=False,
            is_hidden=False,
            requires_approval=False,
        )
        # Create a soft-deleted comment
        deleted_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This comment was deleted",
            is_moderated=False,
            is_hidden=False,
            requires_approval=False,
            deleted_at=datetime.now(timezone.utc),
            deleted_by=test_user.id,
            deletion_reason="Removed by moderator",
        )
        db_session.add(visible_comment)
        db_session.add(deleted_comment)
        db_session.commit()

        repo = IdeaRepository(db_session)
        results = repo.get_ideas_with_scores(
            category_id=test_idea.category_id, current_user_id=None
        )

        # Should only count the visible comment
        assert len(results) == 1
        assert results[0].comment_count == 1

    def test_leaderboard_comment_count_excludes_hidden_comments(
        self, db_session, test_user, test_idea
    ):
        """Comment count in leaderboard excludes hidden (flagged) comments."""
        # Create a visible comment
        visible_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This is a visible comment",
            is_moderated=False,
            is_hidden=False,
            requires_approval=False,
        )
        # Create a hidden comment
        hidden_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This comment is hidden due to flags",
            is_moderated=False,
            is_hidden=True,
            hidden_at=datetime.now(timezone.utc),
            flag_count=3,
            requires_approval=False,
        )
        db_session.add(visible_comment)
        db_session.add(hidden_comment)
        db_session.commit()

        repo = IdeaRepository(db_session)
        results = repo.get_ideas_with_scores(
            category_id=test_idea.category_id, current_user_id=None
        )

        # Should only count the visible comment
        assert len(results) == 1
        assert results[0].comment_count == 1

    def test_leaderboard_comment_count_excludes_pending_approval_comments(
        self, db_session, test_user, test_idea
    ):
        """Comment count in leaderboard excludes comments pending approval."""
        # Create a visible comment
        visible_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This is an approved comment",
            is_moderated=False,
            is_hidden=False,
            requires_approval=False,
        )
        # Create a comment pending approval
        pending_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This comment is pending approval",
            is_moderated=False,
            is_hidden=False,
            requires_approval=True,
        )
        db_session.add(visible_comment)
        db_session.add(pending_comment)
        db_session.commit()

        repo = IdeaRepository(db_session)
        results = repo.get_ideas_with_scores(
            category_id=test_idea.category_id, current_user_id=None
        )

        # Should only count the approved comment
        assert len(results) == 1
        assert results[0].comment_count == 1

    def test_leaderboard_comment_count_excludes_moderated_comments(
        self, db_session, test_user, test_idea
    ):
        """Comment count in leaderboard excludes moderated comments."""
        # Create a visible comment
        visible_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This is a visible comment",
            is_moderated=False,
            is_hidden=False,
            requires_approval=False,
        )
        # Create a moderated comment
        moderated_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="This comment was moderated",
            is_moderated=True,
            is_hidden=False,
            requires_approval=False,
        )
        db_session.add(visible_comment)
        db_session.add(moderated_comment)
        db_session.commit()

        repo = IdeaRepository(db_session)
        results = repo.get_ideas_with_scores(
            category_id=test_idea.category_id, current_user_id=None
        )

        # Should only count the visible comment
        assert len(results) == 1
        assert results[0].comment_count == 1

    def test_leaderboard_comment_count_excludes_all_non_visible_comments(
        self, db_session, test_user, test_idea
    ):
        """Comment count excludes deleted, hidden, pending, and moderated comments."""
        # Create visible comments
        for i in range(3):
            comment = db_models.Comment(
                idea_id=test_idea.id,
                user_id=test_user.id,
                content=f"Visible comment {i}",
                is_moderated=False,
                is_hidden=False,
                requires_approval=False,
            )
            db_session.add(comment)

        # Create a deleted comment
        deleted_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Deleted comment",
            is_moderated=False,
            deleted_at=datetime.now(timezone.utc),
        )
        db_session.add(deleted_comment)

        # Create a hidden comment
        hidden_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Hidden comment",
            is_moderated=False,
            is_hidden=True,
            hidden_at=datetime.now(timezone.utc),
        )
        db_session.add(hidden_comment)

        # Create a pending approval comment
        pending_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Pending approval comment",
            is_moderated=False,
            requires_approval=True,
        )
        db_session.add(pending_comment)

        # Create a moderated comment
        moderated_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Moderated comment",
            is_moderated=True,
        )
        db_session.add(moderated_comment)

        db_session.commit()

        repo = IdeaRepository(db_session)
        results = repo.get_ideas_with_scores(
            category_id=test_idea.category_id, current_user_id=None
        )

        # Should only count the 3 visible comments
        assert len(results) == 1
        assert results[0].comment_count == 3

    def test_leaderboard_comment_count_zero_when_no_visible_comments(
        self, db_session, test_user, test_idea
    ):
        """Comment count is 0 when all comments are non-visible."""
        # Create only non-visible comments
        deleted_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Deleted comment",
            is_moderated=False,
            deleted_at=datetime.now(timezone.utc),
        )
        hidden_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Hidden comment",
            is_moderated=False,
            is_hidden=True,
        )
        db_session.add(deleted_comment)
        db_session.add(hidden_comment)
        db_session.commit()

        repo = IdeaRepository(db_session)
        results = repo.get_ideas_with_scores(
            category_id=test_idea.category_id, current_user_id=None
        )

        # Should have 0 comments counted
        assert len(results) == 1
        assert results[0].comment_count == 0

    def test_get_ideas_by_ids_comment_count_excludes_non_visible(
        self, db_session, test_user, test_idea
    ):
        """get_ideas_by_ids_with_scores also excludes non-visible comments from count."""
        # Create visible comment
        visible_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Visible comment",
            is_moderated=False,
            is_hidden=False,
            requires_approval=False,
        )
        # Create non-visible comments
        deleted_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Deleted comment",
            is_moderated=False,
            deleted_at=datetime.now(timezone.utc),
        )
        pending_comment = db_models.Comment(
            idea_id=test_idea.id,
            user_id=test_user.id,
            content="Pending comment",
            is_moderated=False,
            requires_approval=True,
        )
        db_session.add(visible_comment)
        db_session.add(deleted_comment)
        db_session.add(pending_comment)
        db_session.commit()

        repo = IdeaRepository(db_session)
        results = repo.get_ideas_by_ids_with_scores(
            idea_ids=[test_idea.id], current_user_id=None
        )

        # Should only count the visible comment
        assert len(results) == 1
        assert results[0].comment_count == 1
