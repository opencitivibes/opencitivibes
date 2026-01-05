"""Tests for AccountDeletionService."""

import pytest
from sqlalchemy.orm import Session

import models.schemas as schemas
from models.exceptions import (
    AuthenticationException,
    NotFoundException,
    ValidationException,
)
from repositories.db_models import User, Vote
from services.account_deletion_service import AccountDeletionService


class TestAccountDeletionService:
    """Tests for account deletion functionality."""

    def test_delete_account_success_with_anonymize(
        self, db_session: Session, test_user_with_password: User
    ) -> None:
        """Test successful account deletion with content anonymization."""
        request = schemas.DeleteAccountRequest(
            password="TestPassword123!",
            confirmation_text="DELETE MY ACCOUNT",
            delete_content=False,
        )

        result = AccountDeletionService.delete_account(
            db_session, test_user_with_password.id, request
        )

        assert result.message == "Your account has been deleted successfully."
        assert result.content_anonymized is True
        assert result.data_deleted is False

        # Verify user is anonymized
        db_session.refresh(test_user_with_password)
        assert test_user_with_password.is_active is False
        assert "deleted-user-" in test_user_with_password.email
        assert test_user_with_password.display_name == "Deleted User"

    def test_delete_account_success_with_content_deletion(
        self, db_session: Session, test_user_with_password: User
    ) -> None:
        """Test successful account deletion with full content deletion."""
        request = schemas.DeleteAccountRequest(
            password="TestPassword123!",
            confirmation_text="DELETE MY ACCOUNT",
            delete_content=True,
        )

        result = AccountDeletionService.delete_account(
            db_session, test_user_with_password.id, request
        )

        assert result.message == "Your account has been deleted successfully."
        assert result.content_anonymized is False
        assert result.data_deleted is True

    def test_delete_account_wrong_password(
        self, db_session: Session, test_user_with_password: User
    ) -> None:
        """Test deletion fails with wrong password."""
        request = schemas.DeleteAccountRequest(
            password="WrongPassword123!",
            confirmation_text="DELETE MY ACCOUNT",
            delete_content=False,
        )

        with pytest.raises(AuthenticationException) as exc_info:
            AccountDeletionService.delete_account(
                db_session, test_user_with_password.id, request
            )

        assert "Incorrect password" in str(exc_info.value)

    def test_delete_account_wrong_confirmation(
        self, db_session: Session, test_user_with_password: User
    ) -> None:
        """Test deletion fails with wrong confirmation text."""
        request = schemas.DeleteAccountRequest(
            password="TestPassword123!",
            confirmation_text="I WANT TO DELETE",  # Wrong text
            delete_content=False,
        )

        with pytest.raises(ValidationException) as exc_info:
            AccountDeletionService.delete_account(
                db_session, test_user_with_password.id, request
            )

        assert "confirmation phrase" in str(exc_info.value)

    def test_delete_account_user_not_found(self, db_session: Session) -> None:
        """Test deletion fails when user doesn't exist."""
        request = schemas.DeleteAccountRequest(
            password="TestPassword123!",
            confirmation_text="DELETE MY ACCOUNT",
            delete_content=False,
        )

        with pytest.raises(NotFoundException) as exc_info:
            AccountDeletionService.delete_account(db_session, 99999, request)

        assert "User not found" in str(exc_info.value)

    def test_delete_account_removes_votes(
        self,
        db_session: Session,
        test_user_with_password: User,
        test_user_vote: Vote,
    ) -> None:
        """Test that votes are removed on account deletion."""
        user_id = test_user_with_password.id

        request = schemas.DeleteAccountRequest(
            password="TestPassword123!",
            confirmation_text="DELETE MY ACCOUNT",
            delete_content=False,
        )

        AccountDeletionService.delete_account(db_session, user_id, request)

        # Verify votes are deleted
        remaining_votes = db_session.query(Vote).filter(Vote.user_id == user_id).count()
        assert remaining_votes == 0

    def test_delete_account_case_insensitive_confirmation(
        self, db_session: Session, test_user_with_password: User
    ) -> None:
        """Test confirmation text is case insensitive."""
        request = schemas.DeleteAccountRequest(
            password="TestPassword123!",
            confirmation_text="Delete My Account",  # Mixed case
            delete_content=False,
        )

        # Should work since we use .upper() comparison
        result = AccountDeletionService.delete_account(
            db_session, test_user_with_password.id, request
        )

        assert result.message == "Your account has been deleted successfully."
