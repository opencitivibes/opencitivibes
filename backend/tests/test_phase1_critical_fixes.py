"""
Unit tests for Phase 1: Critical Fixes

Tests cover:
- Task 1.1: HTTPException replaced with domain exceptions in services
- Task 1.2: SECRET_KEY configuration (tested via conftest.py setup)
- Task 1.3: N+1 query fix in IdeaRepository
- Task 1.4: Database indexes (tested via model inspection)
"""

import pytest
from sqlalchemy.exc import IntegrityError
from unittest.mock import patch

from models.exceptions import (
    NotFoundException,
    AlreadyExistsException,
    BusinessRuleException,
    ValidationException,
)
from services.category_service import CategoryService
from services.user_service import UserService
from repositories.idea_repository import IdeaRepository
import repositories.db_models as db_models
import models.schemas as schemas


class TestTask11CategoryServiceExceptions:
    """Test that CategoryService raises domain exceptions instead of HTTPException."""

    def test_create_category_integrity_error_raises_already_exists(self, db_session):
        """Test that IntegrityError during category creation raises AlreadyExistsException.

        Note: Category names don't have unique constraints in the current schema,
        so we mock the IntegrityError to test the exception handling path.
        """
        category_data = schemas.CategoryCreate(
            name_en="Test Category",
            name_fr="Catégorie Test",
            description_en="Description",
            description_fr="Description",
        )

        # Mock the commit to raise IntegrityError
        with patch.object(
            db_session, "commit", side_effect=IntegrityError("", "", Exception())
        ):
            with pytest.raises(AlreadyExistsException) as exc_info:
                CategoryService.create_category(db_session, category_data)

            assert "already exists" in str(exc_info.value.message).lower()

    def test_update_category_raises_not_found(self, db_session):
        """Test that updating non-existent category raises NotFoundException."""
        update_data = schemas.CategoryUpdate(name_en="New Name")

        with pytest.raises(NotFoundException) as exc_info:
            CategoryService.update_category(db_session, 99999, update_data)

        assert "not found" in str(exc_info.value.message).lower()

    def test_delete_category_raises_not_found(self, db_session):
        """Test that deleting non-existent category raises NotFoundException."""
        with pytest.raises(NotFoundException) as exc_info:
            CategoryService.delete_category(db_session, 99999)

        assert "not found" in str(exc_info.value.message).lower()

    def test_delete_category_raises_business_rule_with_ideas(
        self, db_session, test_category, test_idea
    ):
        """Test that deleting category with ideas raises BusinessRuleException."""
        with pytest.raises(BusinessRuleException) as exc_info:
            CategoryService.delete_category(db_session, test_category.id)

        assert "cannot delete" in str(exc_info.value.message).lower()
        assert "associated ideas" in str(exc_info.value.message).lower()

    def test_get_category_statistics_raises_not_found(self, db_session):
        """Test that getting stats for non-existent category raises NotFoundException."""
        with pytest.raises(NotFoundException) as exc_info:
            CategoryService.get_category_statistics(db_session, 99999)

        assert "not found" in str(exc_info.value.message).lower()


class TestTask11UserServiceExceptions:
    """Test that UserService raises domain exceptions instead of HTTPException."""

    def test_update_user_raises_not_found(self, db_session):
        """Test that updating non-existent user raises NotFoundException."""
        update_data = schemas.UserUpdate(is_active=True)

        with pytest.raises(NotFoundException) as exc_info:
            UserService.update_user(db_session, 99999, update_data)

        assert "not found" in str(exc_info.value.message).lower()

    def test_delete_user_raises_not_found(self, db_session):
        """Test that deleting non-existent user raises NotFoundException."""
        with pytest.raises(NotFoundException) as exc_info:
            UserService.delete_user(db_session, 99999)

        assert "not found" in str(exc_info.value.message).lower()

    def test_assign_admin_role_raises_not_found_for_user(self, db_session):
        """Test that assigning admin role to non-existent user raises NotFoundException."""
        with pytest.raises(NotFoundException) as exc_info:
            UserService.assign_admin_role(db_session, 99999, category_id=1)

        assert "user not found" in str(exc_info.value.message).lower()

    def test_assign_admin_role_raises_not_found_for_category(
        self, db_session, test_user
    ):
        """Test that assigning admin role with non-existent category raises NotFoundException."""
        with pytest.raises(NotFoundException) as exc_info:
            UserService.assign_admin_role(db_session, test_user.id, category_id=99999)

        assert "category not found" in str(exc_info.value.message).lower()

    def test_assign_admin_role_raises_validation_for_duplicate(
        self, db_session, test_user, test_category
    ):
        """Test that assigning duplicate admin role raises ValidationException."""
        # First assignment should succeed
        UserService.assign_admin_role(db_session, test_user.id, test_category.id)

        # Second assignment should fail
        with pytest.raises(ValidationException) as exc_info:
            UserService.assign_admin_role(db_session, test_user.id, test_category.id)

        assert "already exists" in str(exc_info.value.message).lower()

    def test_remove_admin_role_raises_not_found(self, db_session, test_user):
        """Test that removing non-existent admin role raises NotFoundException."""
        with pytest.raises(NotFoundException) as exc_info:
            UserService.remove_admin_role(db_session, test_user.id, category_id=99999)

        assert "not found" in str(exc_info.value.message).lower()

    def test_get_user_statistics_raises_not_found(self, db_session):
        """Test that getting stats for non-existent user raises NotFoundException."""
        with pytest.raises(NotFoundException) as exc_info:
            UserService.get_user_statistics(db_session, 99999)

        assert "not found" in str(exc_info.value.message).lower()


class TestTask13N1QueryFix:
    """Test that the N+1 query fix works correctly."""

    def test_fetch_tags_batch_returns_empty_for_no_ids(self, db_session):
        """Test that _fetch_tags_batch returns empty dict for empty list."""
        repo = IdeaRepository(db_session)
        result = repo._fetch_tags_batch([])
        assert result == {}

    def test_fetch_tags_batch_returns_tags_by_idea(
        self, db_session, test_idea, test_tag
    ):
        """Test that _fetch_tags_batch returns tags grouped by idea ID."""
        # Link tag to idea
        idea_tag = db_models.IdeaTag(idea_id=test_idea.id, tag_id=test_tag.id)
        db_session.add(idea_tag)
        db_session.commit()

        repo = IdeaRepository(db_session)
        result = repo._fetch_tags_batch([test_idea.id])

        assert test_idea.id in result
        assert len(result[test_idea.id]) == 1
        assert result[test_idea.id][0].name == test_tag.name

    def test_fetch_tags_batch_handles_ideas_without_tags(self, db_session, test_idea):
        """Test that _fetch_tags_batch handles ideas without tags."""
        repo = IdeaRepository(db_session)
        result = repo._fetch_tags_batch([test_idea.id])

        # Idea with no tags should not be in result
        assert test_idea.id not in result

    def test_get_ideas_with_scores_uses_batch_fetch(
        self, db_session, test_idea, test_tag
    ):
        """Test that get_ideas_with_scores uses batch tag fetching."""
        # Link tag to idea
        idea_tag = db_models.IdeaTag(idea_id=test_idea.id, tag_id=test_tag.id)
        db_session.add(idea_tag)
        db_session.commit()

        repo = IdeaRepository(db_session)

        # Patch _fetch_tags_batch to verify it's called
        with patch.object(
            repo, "_fetch_tags_batch", wraps=repo._fetch_tags_batch
        ) as mock_fetch:
            result = repo.get_ideas_with_scores(
                status_filter=db_models.IdeaStatus.APPROVED
            )

            # Verify batch fetch was called once (not N times)
            mock_fetch.assert_called_once()

            # Verify result contains tags
            assert len(result) == 1
            assert len(result[0].tags) == 1
            assert result[0].tags[0].name == test_tag.name


class TestTask14DatabaseIndexes:
    """Test that database indexes are properly defined."""

    def test_idea_model_has_indexes(self):
        """Test that Idea model has the required indexes."""
        table_args = db_models.Idea.__table_args__

        # Extract index names
        index_names = [
            arg.name for arg in table_args if hasattr(arg, "name") and arg.name
        ]

        assert "ix_ideas_status" in index_names
        assert "ix_ideas_user_status" in index_names
        assert "ix_ideas_category" in index_names

    def test_vote_model_has_indexes(self):
        """Test that Vote model has the required indexes."""
        table_args = db_models.Vote.__table_args__

        # Extract index names
        index_names = [
            arg.name for arg in table_args if hasattr(arg, "name") and arg.name
        ]

        assert "ix_votes_idea" in index_names
        assert "ix_votes_user_idea" in index_names

    def test_comment_model_has_index(self):
        """Test that Comment model has the required index."""
        table_args = db_models.Comment.__table_args__

        # table_args is a tuple with single Index
        if isinstance(table_args, tuple):
            index_names = [
                arg.name for arg in table_args if hasattr(arg, "name") and arg.name
            ]
        else:
            index_names = [table_args.name] if hasattr(table_args, "name") else []

        assert "ix_comments_idea_moderated" in index_names


class TestTask12SecretKeyConfiguration:
    """Test that SECRET_KEY configuration is required."""

    @pytest.mark.skipif(
        "PYTEST_XDIST_WORKER" in __import__("os").environ,
        reason="Test manipulates env vars, incompatible with parallel execution",
    )
    def test_settings_requires_secret_key(self):
        """Test that Settings requires SECRET_KEY to be set."""
        import os
        from pydantic import ValidationError

        # Save current value
        original_value = os.environ.get("SECRET_KEY")

        try:
            # Remove SECRET_KEY from environment
            if "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]

            # Import fresh Settings class
            from importlib import reload
            import models.config as config_module

            # This should raise ValidationError because SECRET_KEY is required
            with pytest.raises(ValidationError):
                reload(config_module)
        finally:
            # Restore original value
            if original_value is not None:
                os.environ["SECRET_KEY"] = original_value
            elif "SECRET_KEY" in os.environ:
                del os.environ["SECRET_KEY"]

            # Set it back for other tests
            os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
