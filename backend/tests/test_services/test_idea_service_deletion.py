"""
Tests for idea soft delete functionality in IdeaService.
"""

import pytest

from models.exceptions import (
    CannotDeleteOthersIdeaException,
    IdeaAlreadyDeletedException,
    IdeaNotDeletedException,
    NotFoundException,
)
from services.idea_service import IdeaService


class TestIdeaSoftDelete:
    """Tests for soft delete functionality."""

    def test_user_can_delete_own_idea(
        self, db_session, test_user, test_idea, test_category
    ):
        """User can soft delete their own idea."""
        deleted = IdeaService.soft_delete_idea(
            db=db_session,
            idea_id=test_idea.id,
            user_id=test_user.id,
            reason="No longer relevant",
        )

        assert deleted.deleted_at is not None
        assert deleted.deleted_by == test_user.id
        assert deleted.deletion_reason == "No longer relevant"

    def test_user_can_delete_own_idea_without_reason(
        self, db_session, test_user, test_idea
    ):
        """User can soft delete their own idea without providing a reason."""
        deleted = IdeaService.soft_delete_idea(
            db=db_session,
            idea_id=test_idea.id,
            user_id=test_user.id,
        )

        assert deleted.deleted_at is not None
        assert deleted.deleted_by == test_user.id
        assert deleted.deletion_reason is None

    def test_user_cannot_delete_others_idea(self, db_session, test_idea, other_user):
        """User cannot delete another user's idea."""
        with pytest.raises(CannotDeleteOthersIdeaException):
            IdeaService.soft_delete_idea(
                db=db_session,
                idea_id=test_idea.id,
                user_id=other_user.id,
            )

    def test_admin_can_delete_any_idea(self, db_session, admin_user, test_idea):
        """Admin can delete any user's idea."""
        deleted = IdeaService.soft_delete_idea(
            db=db_session,
            idea_id=test_idea.id,
            user_id=admin_user.id,
            reason="Spam content",
            is_admin=True,
        )

        assert deleted.deleted_at is not None
        assert deleted.deleted_by == admin_user.id
        assert deleted.deletion_reason == "Spam content"

    def test_cannot_delete_already_deleted_idea(
        self, db_session, test_user, deleted_idea
    ):
        """Cannot delete an already deleted idea."""
        with pytest.raises(IdeaAlreadyDeletedException):
            IdeaService.soft_delete_idea(
                db=db_session,
                idea_id=deleted_idea.id,
                user_id=test_user.id,
            )

    def test_cannot_delete_nonexistent_idea(self, db_session, test_user):
        """Cannot delete an idea that doesn't exist."""
        with pytest.raises(NotFoundException):
            IdeaService.soft_delete_idea(
                db=db_session,
                idea_id=99999,
                user_id=test_user.id,
            )


class TestIdeaRestore:
    """Tests for idea restoration functionality."""

    def test_admin_can_restore_deleted_idea(self, db_session, deleted_idea):
        """Admin can restore a soft-deleted idea."""
        restored = IdeaService.restore_idea(db_session, deleted_idea.id)

        assert restored.deleted_at is None
        assert restored.deleted_by is None
        assert restored.deletion_reason is None

    def test_cannot_restore_non_deleted_idea(self, db_session, test_idea):
        """Cannot restore an idea that isn't deleted."""
        with pytest.raises(IdeaNotDeletedException):
            IdeaService.restore_idea(db_session, test_idea.id)

    def test_cannot_restore_nonexistent_idea(self, db_session):
        """Cannot restore an idea that doesn't exist."""
        with pytest.raises(NotFoundException):
            IdeaService.restore_idea(db_session, 99999)


class TestDeletedIdeaVisibility:
    """Tests for visibility of deleted ideas in queries."""

    def test_deleted_idea_not_found_by_get_idea_by_id(self, db_session, deleted_idea):
        """Deleted ideas should not be found by get_idea_by_id."""
        result = IdeaService.get_idea_by_id(db_session, deleted_idea.id)
        assert result is None

    def test_deleted_idea_found_with_include_deleted_flag(
        self, db_session, deleted_idea
    ):
        """Deleted ideas can be found with include_deleted=True."""
        result = IdeaService.get_idea_by_id(
            db_session, deleted_idea.id, include_deleted=True
        )
        assert result is not None
        assert result.id == deleted_idea.id

    def test_deleted_idea_not_in_get_ideas_by_status(self, db_session, deleted_idea):
        """Deleted ideas should not appear in status queries."""
        import repositories.db_models as db_models

        ideas = IdeaService.get_ideas_by_status(
            db_session, db_models.IdeaStatus.APPROVED
        )
        idea_ids = [i.id for i in ideas]
        assert deleted_idea.id not in idea_ids

    def test_deleted_idea_not_in_get_ideas_by_user(
        self, db_session, test_user, deleted_idea
    ):
        """Deleted ideas should not appear in user's idea list."""
        ideas = IdeaService.get_ideas_by_user(db_session, test_user.id)
        idea_ids = [i.id for i in ideas]
        assert deleted_idea.id not in idea_ids


class TestGetDeletedIdeas:
    """Tests for admin listing of deleted ideas."""

    def test_get_deleted_ideas_returns_deleted(self, db_session, deleted_idea):
        """get_deleted_ideas returns soft-deleted ideas."""
        ideas, total = IdeaService.get_deleted_ideas(db_session)

        assert total == 1
        assert len(ideas) == 1
        assert ideas[0].id == deleted_idea.id

    def test_get_deleted_ideas_excludes_non_deleted(
        self, db_session, test_idea, deleted_idea
    ):
        """get_deleted_ideas excludes non-deleted ideas."""
        ideas, total = IdeaService.get_deleted_ideas(db_session)

        idea_ids = [i.id for i in ideas]
        assert test_idea.id not in idea_ids
        assert deleted_idea.id in idea_ids

    def test_get_deleted_ideas_pagination(
        self, db_session, test_user, test_category, admin_user
    ):
        """get_deleted_ideas respects pagination parameters."""
        from datetime import UTC, datetime
        import repositories.db_models as db_models

        # Create multiple deleted ideas
        for i in range(5):
            idea = db_models.Idea(
                title=f"Deleted Idea {i}",
                description=f"Deleted idea {i} description.",
                category_id=test_category.id,
                user_id=test_user.id,
                status=db_models.IdeaStatus.APPROVED,
                deleted_at=datetime.now(UTC),
                deleted_by=admin_user.id,
            )
            db_session.add(idea)
        db_session.commit()

        # Get first page
        ideas, total = IdeaService.get_deleted_ideas(db_session, skip=0, limit=2)
        assert total == 5
        assert len(ideas) == 2

        # Get second page
        ideas, total = IdeaService.get_deleted_ideas(db_session, skip=2, limit=2)
        assert total == 5
        assert len(ideas) == 2
