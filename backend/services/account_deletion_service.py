"""
Account Deletion Service for Law 25 Compliance.

Provides self-service account deletion with anonymization strategy.
Article 28 (Right to Erasure).
"""

from datetime import datetime, timezone
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session

import authentication.auth as auth
import models.schemas as schemas
import repositories.db_models as db_models
from models.exceptions import (
    AuthenticationException,
    NotFoundException,
    ValidationException,
)
from repositories.account_deletion_repository import AccountDeletionRepository
from repositories.consent_log_repository import ConsentLogRepository
from repositories.user_repository import UserRepository


class AccountDeletionService:
    """Service for user account deletion in compliance with Law 25."""

    # Valid confirmation phrases (EN, FR, ES)
    VALID_CONFIRMATION_PHRASES = {
        "DELETE MY ACCOUNT",
        "SUPPRIMER MON COMPTE",
        "ELIMINAR MI CUENTA",
    }

    @staticmethod
    def _validate_deletion_request(
        user: db_models.User,
        request: schemas.DeleteAccountRequest,
        user_id: int,
        ip_address: Optional[str],
    ) -> None:
        """Validate deletion request (confirmation text and password)."""
        if (
            request.confirmation_text.upper()
            not in AccountDeletionService.VALID_CONFIRMATION_PHRASES
        ):
            raise ValidationException(
                "Please type the confirmation phrase exactly as shown"
            )

        if not auth.verify_password(request.password, str(user.hashed_password)):
            logger.warning(
                f"Account deletion failed: incorrect password for user {user_id}",
                extra={"user_id": user_id, "ip_address": ip_address},
            )
            raise AuthenticationException("Incorrect password")

    @staticmethod
    def _process_user_content(
        deletion_repo: AccountDeletionRepository,
        user_id: int,
        delete_content: bool,
        now: datetime,
    ) -> bool:
        """Process user content (delete or anonymize)."""
        if delete_content:
            AccountDeletionService._delete_user_content(deletion_repo, user_id, now)
            return False  # content_anonymized = False
        else:
            AccountDeletionService._anonymize_user_content(deletion_repo, user_id)
            return True  # content_anonymized = True

    @staticmethod
    def delete_account(
        db: Session,
        user_id: int,
        request: schemas.DeleteAccountRequest,
        ip_address: Optional[str] = None,
    ) -> schemas.DeleteAccountResponse:
        """Delete user account (self-service) with content handling."""
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")

        AccountDeletionService._validate_deletion_request(
            user, request, user_id, ip_address
        )

        logger.info(
            f"User {user_id} requested account deletion",
            extra={"user_id": user_id, "ip_address": ip_address},
        )

        now = datetime.now(timezone.utc)
        deletion_repo = AccountDeletionRepository(db)

        content_anonymized = AccountDeletionService._process_user_content(
            deletion_repo, user_id, request.delete_content, now
        )

        AccountDeletionService._anonymize_user_profile(user)
        AccountDeletionService._delete_sensitive_data(deletion_repo, user_id)

        ConsentLogRepository(db).create_consent_log(
            user_id=user_id,
            consent_type="account",
            action="deleted",
            ip_address=ip_address,
        )

        return schemas.DeleteAccountResponse(
            message="Your account has been deleted successfully.",
            deleted_at=now,
            data_deleted=request.delete_content,
            content_anonymized=content_anonymized,
        )

    @staticmethod
    def _anonymize_user_profile(user: db_models.User) -> None:
        """Anonymize user profile data."""
        user_id = user.id

        # Replace PII with anonymized values
        user.email = f"deleted-user-{user_id}@deleted.local"  # type: ignore[assignment]
        user.username = f"deleted-user-{user_id}"  # type: ignore[assignment]
        user.display_name = "Deleted User"  # type: ignore[assignment]
        user.avatar_url = None  # type: ignore[assignment]
        user.hashed_password = ""  # type: ignore[assignment]  # nosec B105
        user.is_active = False  # type: ignore[assignment]
        user.is_official = False  # type: ignore[assignment]
        user.official_title = None  # type: ignore[assignment]

        # Mark official fields as cleared
        user.requests_official_status = False  # type: ignore[assignment]
        user.official_title_request = None  # type: ignore[assignment]
        user.official_request_at = None  # type: ignore[assignment]
        user.official_verified_at = None  # type: ignore[assignment]

        # Keep consent records for audit but mark withdrawn
        user.consent_terms_accepted = False  # type: ignore[assignment]
        user.consent_privacy_accepted = False  # type: ignore[assignment]
        user.marketing_consent = False  # type: ignore[assignment]

    @staticmethod
    def _delete_sensitive_data(
        deletion_repo: AccountDeletionRepository,
        user_id: int,
    ) -> None:
        """Delete sensitive user data that shouldn't be retained."""
        deletion_repo.delete_totp_secrets(user_id)
        deletion_repo.delete_backup_codes(user_id)
        deletion_repo.delete_email_login_codes(user_id)
        deletion_repo.delete_admin_roles(user_id)
        deletion_repo.delete_trusted_devices(user_id)

    @staticmethod
    def _anonymize_user_content(
        deletion_repo: AccountDeletionRepository,
        user_id: int,
    ) -> None:
        """
        Anonymize user content (preserve content but remove attribution).

        This approach:
        - Keeps ideas/comments for community value
        - Removes user attribution (shown as 'Deleted User')
        - Is the default/recommended approach
        """
        # Ideas remain but will show 'Deleted User' as author
        # Comments remain but will show 'Deleted User' as author
        # (handled by User record's display_name change)

        # Votes should be deleted (they're personal preferences)
        vote_ids = deletion_repo.get_vote_ids_by_user(user_id)
        if vote_ids:
            deletion_repo.delete_vote_qualities_by_vote_ids(vote_ids)
        deletion_repo.delete_votes_by_user(user_id)

        # Delete comment likes
        deletion_repo.delete_comment_likes_by_user(user_id)

        # Delete flags submitted by user
        deletion_repo.delete_content_flags_by_reporter(user_id)

    @staticmethod
    def _delete_user_content(
        deletion_repo: AccountDeletionRepository,
        user_id: int,
        deleted_at: datetime,
    ) -> None:
        """
        Delete all user content.

        This approach:
        - Removes all ideas, comments, votes
        - Complete data removal
        - Chosen when user wants full deletion
        """
        # Delete vote qualities first (foreign key)
        vote_ids = deletion_repo.get_vote_ids_by_user(user_id)
        if vote_ids:
            deletion_repo.delete_vote_qualities_by_vote_ids(vote_ids)

        # Delete votes
        deletion_repo.delete_votes_by_user(user_id)

        # Delete comment likes by user
        deletion_repo.delete_comment_likes_by_user(user_id)

        # Delete idea tags (foreign key)
        idea_ids = deletion_repo.get_idea_ids_by_user(user_id)
        if idea_ids:
            deletion_repo.delete_idea_tags_by_idea_ids(idea_ids)

        # Soft delete comments (preserve thread structure, mark as deleted)
        deletion_repo.soft_delete_comments_by_user(user_id, deleted_at)

        # Soft delete ideas
        deletion_repo.soft_delete_ideas_by_user(user_id, deleted_at)

        # Delete flags submitted by user
        deletion_repo.delete_content_flags_by_reporter(user_id)
