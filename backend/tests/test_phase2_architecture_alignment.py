"""
Unit tests for Phase 2: Architecture Alignment

Tests cover:
- Task 2.1: AdminRoleService CRUD operations and domain exceptions
- Task 2.2: admin_router.py uses AdminRoleService (no direct DB queries)
- Task 2.3: IdeaService.get_idea_with_score method
- Task 2.4: IdeaService static methods (validate_and_create_idea, get_similar_ideas)
- Task 2.5: categories_router.py pagination removal (no functional test needed)
"""

import pytest

from models.exceptions import (
    NotFoundException,
    AlreadyExistsException,
)
from services.admin_role_service import AdminRoleService
from services.idea_service import IdeaService
import repositories.db_models as db_models
import models.schemas as schemas


class TestTask21AdminRoleService:
    """Test AdminRoleService CRUD operations and domain exceptions."""

    def test_get_user_admin_roles_returns_empty_for_user_without_roles(
        self, db_session, test_user
    ):
        """Test that get_user_admin_roles returns empty list for user without roles."""
        result = AdminRoleService.get_user_admin_roles(db_session, test_user.id)
        assert result == []

    def test_get_user_admin_roles_returns_roles_for_user(
        self, db_session, test_user, test_category
    ):
        """Test that get_user_admin_roles returns roles for user."""
        # Create an admin role
        role = db_models.AdminRole(user_id=test_user.id, category_id=test_category.id)
        db_session.add(role)
        db_session.commit()

        result = AdminRoleService.get_user_admin_roles(db_session, test_user.id)
        assert len(result) == 1
        assert result[0].user_id == test_user.id
        assert result[0].category_id == test_category.id

    def test_get_all_admin_roles_returns_all_roles(
        self, db_session, test_user, test_category
    ):
        """Test that get_all_admin_roles returns all admin roles."""
        # Create an admin role
        role = db_models.AdminRole(user_id=test_user.id, category_id=test_category.id)
        db_session.add(role)
        db_session.commit()

        result = AdminRoleService.get_all_admin_roles(db_session)
        assert len(result) == 1

    def test_create_admin_role_success(self, db_session, test_user, test_category):
        """Test successful admin role creation."""
        result = AdminRoleService.create_admin_role(
            db_session, test_user.id, test_category.id
        )

        assert result.user_id == test_user.id
        assert result.category_id == test_category.id
        assert result.id is not None

    def test_create_admin_role_raises_not_found_for_user(
        self, db_session, test_category
    ):
        """Test that create_admin_role raises NotFoundException for non-existent user."""
        with pytest.raises(NotFoundException) as exc_info:
            AdminRoleService.create_admin_role(db_session, 99999, test_category.id)

        assert "user" in str(exc_info.value.message).lower()
        assert "not found" in str(exc_info.value.message).lower()

    def test_create_admin_role_raises_not_found_for_category(
        self, db_session, test_user
    ):
        """Test that create_admin_role raises NotFoundException for non-existent category."""
        with pytest.raises(NotFoundException) as exc_info:
            AdminRoleService.create_admin_role(db_session, test_user.id, 99999)

        assert "category" in str(exc_info.value.message).lower()
        assert "not found" in str(exc_info.value.message).lower()

    def test_create_admin_role_raises_already_exists_for_duplicate(
        self, db_session, test_user, test_category
    ):
        """Test that create_admin_role raises AlreadyExistsException for duplicate."""
        # Create first role
        AdminRoleService.create_admin_role(db_session, test_user.id, test_category.id)

        # Try to create duplicate
        with pytest.raises(AlreadyExistsException) as exc_info:
            AdminRoleService.create_admin_role(
                db_session, test_user.id, test_category.id
            )

        assert "already exists" in str(exc_info.value.message).lower()

    def test_delete_admin_role_success(self, db_session, test_user, test_category):
        """Test successful admin role deletion."""
        role = AdminRoleService.create_admin_role(
            db_session, test_user.id, test_category.id
        )
        role_id = role.id

        AdminRoleService.delete_admin_role(db_session, role_id)

        # Verify role is deleted
        roles = AdminRoleService.get_user_admin_roles(db_session, test_user.id)
        assert len(roles) == 0

    def test_delete_admin_role_raises_not_found(self, db_session):
        """Test that delete_admin_role raises NotFoundException for non-existent role."""
        with pytest.raises(NotFoundException) as exc_info:
            AdminRoleService.delete_admin_role(db_session, 99999)

        assert "not found" in str(exc_info.value.message).lower()

    def test_is_category_admin_returns_true_when_admin(
        self, db_session, test_user, test_category
    ):
        """Test that is_category_admin returns True when user is admin."""
        AdminRoleService.create_admin_role(db_session, test_user.id, test_category.id)

        result = AdminRoleService.is_category_admin(
            db_session, test_user.id, test_category.id
        )
        assert result is True

    def test_is_category_admin_returns_false_when_not_admin(
        self, db_session, test_user, test_category
    ):
        """Test that is_category_admin returns False when user is not admin."""
        result = AdminRoleService.is_category_admin(
            db_session, test_user.id, test_category.id
        )
        assert result is False


class TestTask23IdeaServiceGetIdeaWithScore:
    """Test IdeaService.get_idea_with_score method."""

    def test_get_idea_with_score_returns_approved_idea(
        self, db_session, test_idea, test_user
    ):
        """Test that get_idea_with_score returns approved idea."""
        result = IdeaService.get_idea_with_score(db_session, test_idea.id, test_user.id)

        assert result.id == test_idea.id
        assert result.title == test_idea.title

    def test_get_idea_with_score_raises_not_found_for_nonexistent(self, db_session):
        """Test that get_idea_with_score raises NotFoundException for non-existent idea."""
        with pytest.raises(NotFoundException) as exc_info:
            IdeaService.get_idea_with_score(db_session, 99999, None)

        assert "not found" in str(exc_info.value.message).lower()

    def test_get_idea_with_score_allows_owner_to_view_pending(
        self, db_session, test_user, test_category
    ):
        """Test that owner can view their pending idea."""
        # Create a pending idea
        pending_idea = db_models.Idea(
            title="Pending Idea",
            description="Pending description",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.PENDING,
        )
        db_session.add(pending_idea)
        db_session.commit()
        db_session.refresh(pending_idea)

        result = IdeaService.get_idea_with_score(
            db_session, pending_idea.id, test_user.id
        )
        assert result.id == pending_idea.id

    def test_get_idea_with_score_hides_pending_from_non_owner(
        self, db_session, test_user, test_category
    ):
        """Test that non-owner cannot view pending idea."""
        # Create another user
        other_user = db_models.User(
            email="other@example.com",
            username="otheruser",
            display_name="Other User",
            hashed_password="hashed",
            is_active=True,
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        # Create a pending idea owned by test_user
        pending_idea = db_models.Idea(
            title="Pending Idea",
            description="Pending description",
            category_id=test_category.id,
            user_id=test_user.id,
            status=db_models.IdeaStatus.PENDING,
        )
        db_session.add(pending_idea)
        db_session.commit()
        db_session.refresh(pending_idea)

        # Other user should not see it
        with pytest.raises(NotFoundException):
            IdeaService.get_idea_with_score(db_session, pending_idea.id, other_user.id)


class TestTask24IdeaServiceStaticMethods:
    """Test that IdeaService methods are static and work correctly."""

    def test_validate_and_create_idea_is_static(self):
        """Test that validate_and_create_idea is a static method."""
        assert isinstance(
            IdeaService.__dict__["validate_and_create_idea"], staticmethod
        )

    def test_get_similar_ideas_is_static(self):
        """Test that get_similar_ideas is a static method."""
        assert isinstance(IdeaService.__dict__["get_similar_ideas"], staticmethod)

    def test_get_idea_with_score_is_static(self):
        """Test that get_idea_with_score is a static method."""
        assert isinstance(IdeaService.__dict__["get_idea_with_score"], staticmethod)

    def test_validate_and_create_idea_raises_not_found_for_category(
        self, db_session, test_user
    ):
        """Test that validate_and_create_idea raises NotFoundException for invalid category."""
        idea_data = schemas.IdeaCreate(
            title="Test Idea",
            description="Test description for the idea",
            category_id=99999,
            tags=[],
        )

        with pytest.raises(NotFoundException) as exc_info:
            IdeaService.validate_and_create_idea(
                db_session, idea_data, test_user.id, "en"
            )

        assert "category not found" in str(exc_info.value.message).lower()

    def test_validate_and_create_idea_creates_idea(
        self, db_session, test_user, test_category
    ):
        """Test that validate_and_create_idea creates an idea successfully."""
        idea_data = schemas.IdeaCreate(
            title="Test Idea",
            description="Test description for the idea that is long enough",
            category_id=test_category.id,
            tags=[],
        )

        result = IdeaService.validate_and_create_idea(
            db_session, idea_data, test_user.id, "en"
        )

        assert result.title == idea_data.title
        assert result.description == idea_data.description
        assert result.category_id == test_category.id
        assert result.user_id == test_user.id
        assert result.status == db_models.IdeaStatus.PENDING

    def test_get_similar_ideas_returns_list(self, db_session, test_idea):
        """Test that get_similar_ideas returns a list."""
        result = IdeaService.get_similar_ideas(
            db_session,
            title="Test Idea Similar",
            description="Similar description",
            category_id=None,
            threshold=0.3,
            limit=5,
            language="en",
        )

        assert isinstance(result, list)


class TestTask21AdminRoleServiceNoHTTPException:
    """Verify AdminRoleService doesn't import HTTPException."""

    def test_admin_role_service_has_no_http_exception(self):
        """Test that AdminRoleService module doesn't import HTTPException."""
        import services.admin_role_service as service_module
        import inspect

        source = inspect.getsource(service_module)
        assert "HTTPException" not in source
        assert "from fastapi" not in source


class TestTask22AdminRouterUsesService:
    """Test that admin_router uses AdminRoleService instead of direct DB queries."""

    def test_admin_router_imports_admin_role_service(self):
        """Test that admin_router imports AdminRoleService."""
        import routers.admin_router as router_module
        import inspect

        source = inspect.getsource(router_module)
        assert "from services.admin_role_service import AdminRoleService" in source

    def test_admin_router_no_direct_admin_role_query(self):
        """Test that admin_router doesn't have direct AdminRole queries for CRUD."""
        import routers.admin_router as router_module
        import inspect

        source = inspect.getsource(router_module)

        # The refactored router should use AdminRoleService methods
        # Check that CRUD operations use the service
        assert "AdminRoleService.create_admin_role" in source
        assert "AdminRoleService.get_all_admin_roles" in source
        assert "AdminRoleService.delete_admin_role" in source


class TestTask24NoModuleLevelInstantiation:
    """Test that IdeaService is not instantiated at module level."""

    def test_ideas_router_no_module_level_idea_service(self):
        """Test that ideas_router doesn't have module-level IdeaService instantiation."""
        import routers.ideas_router as router_module
        import inspect

        source = inspect.getsource(router_module)

        # Should not have module-level instantiation
        assert "idea_service = IdeaService()" not in source

    def test_admin_router_no_module_level_idea_service(self):
        """Test that admin_router doesn't have module-level IdeaService instantiation."""
        import routers.admin_router as router_module
        import inspect

        source = inspect.getsource(router_module)

        # Should not have module-level instantiation
        assert "idea_service = IdeaService()" not in source


class TestTask25CategoriesRouterNoPagination:
    """Test that categories_router doesn't have unused pagination parameters."""

    def test_categories_router_no_unused_pagination(self):
        """Test that get_categories endpoint doesn't have unused pagination params."""
        import routers.categories_router as router_module
        import inspect

        source = inspect.getsource(router_module)

        # Check that PaginationSkip and PaginationLimit are not imported
        assert "PaginationSkip" not in source
        assert "PaginationLimit" not in source
