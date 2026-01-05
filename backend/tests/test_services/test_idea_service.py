"""Tests for IdeaService."""

import pytest

import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import (
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from services.idea_service import IdeaService, escape_like


class TestEscapeLike:
    """Test cases for the escape_like helper function."""

    def test_escape_percent(self):
        """Percent character is escaped."""
        assert escape_like("100%") == "100\\%"

    def test_escape_underscore(self):
        """Underscore character is escaped."""
        assert escape_like("user_name") == "user\\_name"

    def test_escape_backslash(self):
        """Backslash character is escaped."""
        assert escape_like("path\\file") == "path\\\\file"

    def test_escape_multiple_characters(self):
        """Multiple special characters are escaped."""
        assert escape_like("50% off_sale") == "50\\% off\\_sale"

    def test_escape_normal_text(self):
        """Normal text is unchanged."""
        assert escape_like("hello world") == "hello world"


class TestIdeaService:
    """Test cases for idea operations."""

    def test_get_idea_by_id(self, db_session, test_idea):
        """Can retrieve idea by ID."""
        idea = IdeaService.get_idea_by_id(db_session, test_idea.id)

        assert idea is not None
        assert idea.id == test_idea.id
        assert idea.title == test_idea.title

    def test_get_idea_by_id_not_found(self, db_session):
        """Returns None for non-existent idea."""
        idea = IdeaService.get_idea_by_id(db_session, 99999)

        assert idea is None

    def test_get_idea_with_score_approved(self, db_session, test_idea):
        """Can get approved idea with score."""
        result = IdeaService.get_idea_with_score(
            db=db_session,
            idea_id=test_idea.id,
        )

        assert result is not None
        assert result.id == test_idea.id

    def test_get_idea_with_score_not_found(self, db_session):
        """Raises NotFoundException for non-existent idea."""
        with pytest.raises(NotFoundException):
            IdeaService.get_idea_with_score(db=db_session, idea_id=99999)

    def test_get_idea_with_score_pending_owner_can_view(
        self, db_session, pending_idea, test_user
    ):
        """Owner can view their pending idea."""
        result = IdeaService.get_idea_with_score(
            db=db_session,
            idea_id=pending_idea.id,
            current_user_id=test_user.id,
        )

        assert result is not None
        assert result.id == pending_idea.id

    def test_get_idea_with_score_pending_non_owner_cannot_view(
        self, db_session, pending_idea, admin_user
    ):
        """Non-owner cannot view pending idea."""
        with pytest.raises(NotFoundException):
            IdeaService.get_idea_with_score(
                db=db_session,
                idea_id=pending_idea.id,
                current_user_id=admin_user.id,
            )

    def test_validate_and_create_idea(self, db_session, test_user, test_category):
        """Can create a valid idea."""
        idea_data = schemas.IdeaCreate(
            title="New Idea Title",
            description="A description that is long enough to pass the validation check.",
            category_id=test_category.id,
        )

        result = IdeaService.validate_and_create_idea(
            db=db_session,
            idea=idea_data,
            user_id=test_user.id,
        )

        assert result is not None
        assert result.title == "New Idea Title"
        assert result.status == db_models.IdeaStatus.PENDING

    def test_validate_and_create_idea_invalid_category(self, db_session, test_user):
        """Raises NotFoundException for invalid category."""
        idea_data = schemas.IdeaCreate(
            title="New Idea Title",
            description="A description that is long enough to pass the validation check.",
            category_id=99999,
        )

        with pytest.raises(NotFoundException):
            IdeaService.validate_and_create_idea(
                db=db_session,
                idea=idea_data,
                user_id=test_user.id,
            )

    def test_update_idea_by_owner(self, db_session, pending_idea, test_user):
        """Owner can update their pending idea."""
        update_data = schemas.IdeaUpdate(title="Updated Title")

        result = IdeaService.update_idea(
            db=db_session,
            idea_id=pending_idea.id,
            idea_update=update_data,
            user_id=test_user.id,
        )

        assert result.title == "Updated Title"

    def test_update_idea_non_owner_denied(self, db_session, pending_idea, admin_user):
        """Non-owner cannot update idea."""
        update_data = schemas.IdeaUpdate(title="Hacked Title")

        with pytest.raises(PermissionDeniedException):
            IdeaService.update_idea(
                db=db_session,
                idea_id=pending_idea.id,
                idea_update=update_data,
                user_id=admin_user.id,
            )

    def test_update_approved_idea_denied(self, db_session, test_idea, test_user):
        """Cannot update approved idea."""
        update_data = schemas.IdeaUpdate(title="Updated Title")

        with pytest.raises(ValidationException):
            IdeaService.update_idea(
                db=db_session,
                idea_id=test_idea.id,
                idea_update=update_data,
                user_id=test_user.id,
            )

    def test_delete_idea_by_owner(self, db_session, pending_idea, test_user):
        """Owner can delete their idea."""
        result = IdeaService.delete_idea(
            db=db_session,
            idea_id=pending_idea.id,
            user_id=test_user.id,
        )

        assert result is True
        assert IdeaService.get_idea_by_id(db_session, pending_idea.id) is None

    def test_delete_idea_non_owner_denied(self, db_session, pending_idea, admin_user):
        """Non-owner cannot delete idea."""
        with pytest.raises(PermissionDeniedException):
            IdeaService.delete_idea(
                db=db_session,
                idea_id=pending_idea.id,
                user_id=admin_user.id,
            )

    def test_moderate_idea_approve(self, db_session, pending_idea):
        """Admin can approve idea."""
        moderation = schemas.IdeaModerate(
            status=db_models.IdeaStatus.APPROVED,
            admin_comment="Looks good!",
        )

        result = IdeaService.moderate_idea(
            db=db_session,
            idea_id=pending_idea.id,
            moderation=moderation,
        )

        assert result.status == db_models.IdeaStatus.APPROVED
        assert result.admin_comment == "Looks good!"
        assert result.validated_at is not None

    def test_moderate_idea_reject(self, db_session, pending_idea):
        """Admin can reject idea."""
        moderation = schemas.IdeaModerate(
            status=db_models.IdeaStatus.REJECTED,
            admin_comment="Not appropriate.",
        )

        result = IdeaService.moderate_idea(
            db=db_session,
            idea_id=pending_idea.id,
            moderation=moderation,
        )

        assert result.status == db_models.IdeaStatus.REJECTED
        assert result.admin_comment == "Not appropriate."

    def test_get_leaderboard(self, db_session, test_idea, test_category):
        """Can get leaderboard of approved ideas."""
        result = IdeaService.get_leaderboard(
            db=db_session,
            category_id=test_category.id,
        )

        assert len(result) >= 1
        assert all(idea.status == "approved" for idea in result)

    def test_get_my_ideas(self, db_session, test_user, pending_idea, test_idea):
        """User can get their own ideas."""
        result = IdeaService.get_my_ideas(db=db_session, user_id=test_user.id)

        assert len(result) >= 2  # Both pending and approved

    def test_search_ideas(self, db_session, test_idea):
        """Can search ideas by keyword."""
        result = IdeaService.search_ideas(
            db=db_session,
            query="Test",
        )

        assert len(result) >= 1

    def test_search_ideas_escapes_special_chars(self, db_session, test_idea):
        """Search escapes special LIKE characters."""
        # This should not cause SQL pattern matching issues
        result = IdeaService.search_ideas(
            db=db_session,
            query="100%_test",
        )

        # Should return empty list, not cause an error
        assert isinstance(result, list)
