"""
Admin role repository for database operations.
"""

from sqlalchemy.orm import Session

import repositories.db_models as db_models

from .base import BaseRepository


class AdminRoleRepository(BaseRepository[db_models.AdminRole]):
    """Repository for AdminRole entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize admin role repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.AdminRole, db)

    def get_by_user_id(self, user_id: int) -> list[db_models.AdminRole]:
        """
        Get all admin roles for a user.

        Args:
            user_id: User ID

        Returns:
            List of admin roles for the user
        """
        return (
            self.db.query(db_models.AdminRole)
            .filter(db_models.AdminRole.user_id == user_id)
            .all()
        )

    def get_by_user_and_category(
        self, user_id: int, category_id: int | None
    ) -> db_models.AdminRole | None:
        """
        Get admin role for a specific user and category.

        Args:
            user_id: User ID
            category_id: Category ID (None for global admin role check)

        Returns:
            AdminRole if found, None otherwise
        """
        return (
            self.db.query(db_models.AdminRole)
            .filter(
                db_models.AdminRole.user_id == user_id,
                db_models.AdminRole.category_id == category_id,
            )
            .first()
        )

    def delete_by_user_id(self, user_id: int) -> int:
        """
        Delete all admin roles for a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        count = (
            self.db.query(db_models.AdminRole)
            .filter(db_models.AdminRole.user_id == user_id)
            .delete()
        )
        return count

    def exists(self, user_id: int, category_id: int | None) -> bool:
        """
        Check if an admin role exists for user and category.

        Args:
            user_id: User ID
            category_id: Category ID (None for global admin role check)

        Returns:
            True if role exists, False otherwise
        """
        return (
            self.db.query(db_models.AdminRole)
            .filter(
                db_models.AdminRole.user_id == user_id,
                db_models.AdminRole.category_id == category_id,
            )
            .first()
            is not None
        )

    def is_category_admin(self, user_id: int, category_id: int) -> bool:
        """
        Check if user is admin for a specific category.

        Args:
            user_id: User ID
            category_id: Category ID

        Returns:
            True if user is category admin, False otherwise
        """
        return (
            self.db.query(db_models.AdminRole)
            .filter(
                db_models.AdminRole.user_id == user_id,
                db_models.AdminRole.category_id == category_id,
            )
            .first()
            is not None
        )
