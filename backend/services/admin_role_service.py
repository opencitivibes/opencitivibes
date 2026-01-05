"""
Admin role service for business logic.
"""

from typing import List

from sqlalchemy.orm import Session

import repositories.db_models as db_models
from models.exceptions import (
    AlreadyExistsException,
    NotFoundException,
)
from repositories.admin_role_repository import AdminRoleRepository
from repositories.category_repository import CategoryRepository
from repositories.user_repository import UserRepository


class AdminRoleService:
    """Service for admin role management."""

    @staticmethod
    def get_user_admin_roles(db: Session, user_id: int) -> List[db_models.AdminRole]:
        """
        Get all admin roles for a specific user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            List of admin roles for the user
        """
        admin_role_repo = AdminRoleRepository(db)
        return admin_role_repo.get_by_user_id(user_id)

    @staticmethod
    def get_all_admin_roles(db: Session) -> List[db_models.AdminRole]:
        """
        Get all admin roles in the system.

        Args:
            db: Database session

        Returns:
            List of all admin roles
        """
        admin_role_repo = AdminRoleRepository(db)
        return admin_role_repo.get_all()

    @staticmethod
    def create_admin_role(
        db: Session, user_id: int, category_id: int
    ) -> db_models.AdminRole:
        """
        Create a new admin role.

        Args:
            db: Database session
            user_id: User ID
            category_id: Category ID

        Returns:
            Created admin role

        Raises:
            NotFoundException: If user or category not found
            AlreadyExistsException: If admin role already exists
        """
        # Verify user exists
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")

        # Verify category exists
        category_repo = CategoryRepository(db)
        category = category_repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(f"Category with ID {category_id} not found")

        # Check if role already exists
        admin_role_repo = AdminRoleRepository(db)
        existing_role = admin_role_repo.get_by_user_and_category(user_id, category_id)

        if existing_role:
            raise AlreadyExistsException(
                f"Admin role already exists for user {user_id} and category {category_id}"
            )

        # Create admin role
        db_role = db_models.AdminRole(user_id=user_id, category_id=category_id)
        return admin_role_repo.create(db_role)

    @staticmethod
    def delete_admin_role(db: Session, role_id: int) -> None:
        """
        Delete an admin role.

        Args:
            db: Database session
            role_id: Admin role ID

        Raises:
            NotFoundException: If admin role not found
        """
        admin_role_repo = AdminRoleRepository(db)
        role = admin_role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundException(f"Admin role with ID {role_id} not found")

        admin_role_repo.delete(role)

    @staticmethod
    def is_category_admin(db: Session, user_id: int, category_id: int) -> bool:
        """
        Check if a user is an admin for a specific category.

        Args:
            db: Database session
            user_id: User ID
            category_id: Category ID

        Returns:
            True if user is category admin, False otherwise
        """
        admin_role_repo = AdminRoleRepository(db)
        return admin_role_repo.is_category_admin(user_id, category_id)
