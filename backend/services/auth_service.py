"""
Authentication Service

Handles authentication business logic including login and token management.
"""

from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

import models.schemas as schemas
from authentication.auth import authenticate_user, create_access_token
from models.config import settings
from models.exceptions import InvalidCredentialsException

if TYPE_CHECKING:
    import repositories.db_models as db_models


class AuthService:
    """Service for authentication business logic."""

    @staticmethod
    def login(db: Session, email: str, password: str) -> schemas.Token:
        """
        Authenticate a user and create an access token.

        Args:
            db: Database session
            email: User email
            password: User password

        Returns:
            Token object with access_token and token_type

        Raises:
            InvalidCredentialsException: If email or password is incorrect
        """
        user = authenticate_user(db, email, password)
        if not user:
            raise InvalidCredentialsException("Incorrect email or password")

        # Ensure user is a User object, not bool
        if isinstance(user, bool):
            raise InvalidCredentialsException("Incorrect email or password")

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.email)}, expires_delta=access_token_expires
        )
        # nosec B106: "bearer" is OAuth2 token type, not a password
        return schemas.Token(access_token=access_token, token_type="bearer")  # nosec B106

    @staticmethod
    def update_last_login(db: Session, user: "db_models.User") -> None:
        """
        Update user's last login timestamp (Law 25 Phase 3 compliance).

        This method:
        - Updates last_login_at and last_activity_at timestamps
        - Clears any scheduled anonymization (user is now active)

        Args:
            db: Database session
            user: User who just logged in
        """
        from datetime import datetime, timezone

        from repositories.user_repository import UserRepository

        now = datetime.now(timezone.utc)
        user.last_login_at = now  # type: ignore[assignment]
        user.last_activity_at = now  # type: ignore[assignment]

        # Clear any scheduled anonymization since user is active
        if user.scheduled_anonymization_at is not None:
            user.scheduled_anonymization_at = None  # type: ignore[assignment]
            user.inactivity_warning_sent_at = None  # type: ignore[assignment]

        UserRepository(db).commit()

    @staticmethod
    def refresh_token(user: "db_models.User") -> schemas.Token:
        """
        Create a new access token for an authenticated user.

        This allows users to refresh their token before it expires,
        extending their session without re-entering credentials.

        Args:
            user: The authenticated user requesting token refresh

        Returns:
            Token object with a new access_token and token_type
        """
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.email)}, expires_delta=access_token_expires
        )
        # nosec B106: "bearer" is OAuth2 token type, not a password
        return schemas.Token(access_token=access_token, token_type="bearer")  # nosec B106
