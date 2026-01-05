"""Service for managing official roles."""

import re
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from models.exceptions import (
    BusinessRuleException,
    InsufficientPermissionsException,
    NotFoundException,
)
from repositories import db_models

# Title validation constants
MAX_TITLE_LENGTH = 100
# Allow Unicode word chars, spaces, hyphens, periods, commas, apostrophes, parentheses
TITLE_PATTERN = re.compile(r"^[\w\s\-.,\'()]+$", re.UNICODE)


def _validate_official_title(title: Optional[str]) -> Optional[str]:
    """Validate and sanitize official title."""
    if title is None:
        return None

    title = title.strip()

    if len(title) == 0:
        return None

    if len(title) > MAX_TITLE_LENGTH:
        raise BusinessRuleException(
            f"Title must be less than {MAX_TITLE_LENGTH} characters"
        )

    if not TITLE_PATTERN.match(title):
        raise BusinessRuleException("Title contains invalid characters")

    return title


class OfficialService:
    """Service for managing official roles."""

    @staticmethod
    def grant_official_status(
        db: Session,
        user_id: int,
        official_title: Optional[str] = None,
        granted_by: Optional[db_models.User] = None,
    ) -> db_models.User:
        """
        Grant official status to a user.

        Only global admins can grant official status.

        Args:
            db: Database session.
            user_id: ID of the user to grant official status.
            official_title: Optional title for the official.
            granted_by: The admin user granting the status.

        Returns:
            The updated user.

        Raises:
            InsufficientPermissionsException: If granting user is not a global admin.
            NotFoundException: If user not found.
            BusinessRuleException: If user is already an official.
        """
        from repositories.user_repository import UserRepository

        if granted_by and not bool(granted_by.is_global_admin):
            raise InsufficientPermissionsException(
                "Only global admins can grant official status"
            )

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)

        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")

        if user.is_official:
            raise BusinessRuleException("User is already an official")

        # Validate title
        validated_title = _validate_official_title(official_title)

        user.is_official = True
        user.official_title = validated_title
        user.official_verified_at = datetime.now(timezone.utc)

        # Clear the request fields if they were set
        user.requests_official_status = False
        user.official_title_request = None
        user.official_request_at = None

        user_repo.commit()
        user_repo.refresh(user)

        # Audit log
        if granted_by:
            from services.audit_service import AuditAction, AuditService

            AuditService.log(
                user_id=granted_by.id,
                action=AuditAction.OFFICIAL_GRANTED,
                target_type="user",
                target_id=user_id,
                details={"official_title": validated_title},
            )

        return user

    @staticmethod
    def revoke_official_status(
        db: Session,
        user_id: int,
        revoked_by: Optional[db_models.User] = None,
    ) -> db_models.User:
        """
        Revoke official status from a user.

        Only global admins can revoke official status.

        Args:
            db: Database session.
            user_id: ID of the user to revoke official status.
            revoked_by: The admin user revoking the status.

        Returns:
            The updated user.

        Raises:
            InsufficientPermissionsException: If revoking user is not a global admin.
            NotFoundException: If user not found.
            BusinessRuleException: If user is not an official.
        """
        from repositories.user_repository import UserRepository

        if revoked_by and not bool(revoked_by.is_global_admin):
            raise InsufficientPermissionsException(
                "Only global admins can revoke official status"
            )

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)

        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")

        if not user.is_official:
            raise BusinessRuleException("User is not an official")

        user.is_official = False
        user.official_title = None
        user.official_verified_at = None

        user_repo.update(user)

        # Audit log
        if revoked_by:
            from services.audit_service import AuditAction, AuditService

            AuditService.log(
                user_id=revoked_by.id,
                action=AuditAction.OFFICIAL_REVOKED,
                target_type="user",
                target_id=user_id,
            )

        return user

    @staticmethod
    def update_official_title(
        db: Session,
        user_id: int,
        official_title: str,
        updated_by: Optional[db_models.User] = None,
    ) -> db_models.User:
        """
        Update an official's title.

        Args:
            db: Database session.
            user_id: ID of the official user.
            official_title: New title for the official.
            updated_by: The admin user updating the title.

        Returns:
            The updated user.

        Raises:
            InsufficientPermissionsException: If updating user is not a global admin.
            NotFoundException: If user not found.
            BusinessRuleException: If user is not an official.
        """
        from repositories.user_repository import UserRepository

        if updated_by and not bool(updated_by.is_global_admin):
            raise InsufficientPermissionsException(
                "Only global admins can update official titles"
            )

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)

        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")

        if not user.is_official:
            raise BusinessRuleException("User is not an official")

        # Validate title
        validated_title = _validate_official_title(official_title)

        old_title = user.official_title
        user.official_title = validated_title
        user_repo.update(user)

        # Audit log
        if updated_by:
            from services.audit_service import AuditAction, AuditService

            AuditService.log(
                user_id=updated_by.id,
                action=AuditAction.OFFICIAL_TITLE_UPDATED,
                target_type="user",
                target_id=user_id,
                details={"old_title": old_title, "new_title": validated_title},
            )

        return user

    @staticmethod
    def get_all_officials(db: Session) -> List[db_models.User]:
        """
        Get all users with official status.

        Args:
            db: Database session.

        Returns:
            List of official users ordered by verification date (newest first).
        """
        from repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        return user_repo.get_all_officials()

    @staticmethod
    def get_pending_official_requests(db: Session) -> List[db_models.User]:
        """
        Get all users who have requested official status (pending approval).

        Args:
            db: Database session.

        Returns:
            List of users with pending official requests.
        """
        from repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        return user_repo.get_pending_official_requests()

    @staticmethod
    def reject_official_request(
        db: Session,
        user_id: int,
        rejected_by: Optional[db_models.User] = None,
    ) -> db_models.User:
        """
        Reject a user's official status request.

        Args:
            db: Database session.
            user_id: ID of the user whose request to reject.
            rejected_by: The admin user rejecting the request.

        Returns:
            The updated user.

        Raises:
            InsufficientPermissionsException: If rejecting user is not a global admin.
            NotFoundException: If user not found.
            BusinessRuleException: If user has no pending request.
        """
        from repositories.user_repository import UserRepository

        if rejected_by and not bool(rejected_by.is_global_admin):
            raise InsufficientPermissionsException(
                "Only global admins can reject official requests"
            )

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)

        if not user:
            raise NotFoundException(f"User with ID {user_id} not found")

        if not user.requests_official_status:
            raise BusinessRuleException("User has no pending official request")

        user.requests_official_status = False
        user.official_title_request = None
        user.official_request_at = None

        user_repo.update(user)

        # Audit log
        if rejected_by:
            from services.audit_service import AuditAction, AuditService

            AuditService.log(
                user_id=rejected_by.id,
                action=AuditAction.OFFICIAL_REQUEST_REJECTED,
                target_type="user",
                target_id=user_id,
            )

        return user

    @staticmethod
    def is_official(db: Session, user_id: int) -> bool:
        """
        Check if a user is an official.

        Args:
            db: Database session.
            user_id: ID of the user to check.

        Returns:
            True if the user is an official, False otherwise.
        """
        from repositories.user_repository import UserRepository

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        return user is not None and bool(user.is_official)
