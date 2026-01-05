"""Service for 2FA TOTP operations."""

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Union

import jwt
from sqlalchemy.orm import Session

import models.schemas as schemas
from authentication.auth import create_access_token, verify_password
from models.config import settings
from models.exceptions import (
    TwoFactorAlreadyEnabledException,
    TwoFactorConfigurationException,
    TwoFactorInvalidCodeException,
    TwoFactorNotEnabledException,
    TwoFactorSetupIncompleteException,
    TwoFactorTempTokenExpiredException,
    UserNotFoundException,
)
from repositories.totp_repository import BackupCodeRepository, TOTPRepository
from repositories.user_repository import UserRepository

if TYPE_CHECKING:
    import repositories.db_models as db_models


class TOTPService:
    """Service for TOTP 2FA operations."""

    @staticmethod
    def _wrap_config_error(func, *args, **kwargs):
        """Wrap repository calls to convert ValueError to domain exception.

        Repository methods raise ValueError for configuration issues.
        This helper converts them to TwoFactorConfigurationException.
        """
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            raise TwoFactorConfigurationException(str(e)) from e

    @staticmethod
    def setup_2fa(db: Session, user_id: int) -> schemas.TwoFactorSetupResponse:
        """
        Initialize 2FA setup for user.

        Creates a pending TOTP secret that must be verified before activation.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Setup response with secret and QR code URI

        Raises:
            UserNotFoundException: If user not found
            TwoFactorAlreadyEnabledException: If 2FA already enabled
        """
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)

        if not user:
            raise UserNotFoundException("User not found")

        if user.totp_enabled:
            raise TwoFactorAlreadyEnabledException()

        totp_repo = TOTPRepository(db)
        _, plain_secret = TOTPService._wrap_config_error(
            totp_repo.create_totp_secret, user_id
        )
        provisioning_uri = totp_repo.get_provisioning_uri(plain_secret, str(user.email))

        return schemas.TwoFactorSetupResponse(
            secret=plain_secret,
            provisioning_uri=provisioning_uri,
            qr_code_data=provisioning_uri,  # Frontend generates QR from this
        )

    @staticmethod
    def verify_setup(
        db: Session, user_id: int, code: str
    ) -> schemas.TwoFactorVerifySetupResponse:
        """
        Complete 2FA setup by verifying first code.

        Activates 2FA and generates backup codes.

        Args:
            db: Database session
            user_id: User ID
            code: 6-digit TOTP code from authenticator app

        Returns:
            Response with enabled status and backup codes

        Raises:
            TwoFactorSetupIncompleteException: If no pending setup found
            TwoFactorInvalidCodeException: If verification code is invalid
        """
        totp_repo = TOTPRepository(db)
        backup_repo = BackupCodeRepository(db)
        user_repo = UserRepository(db)

        # Verify code against pending secret
        pending = totp_repo.get_pending_totp(user_id)
        if not pending:
            raise TwoFactorSetupIncompleteException()

        is_valid = TOTPService._wrap_config_error(
            totp_repo.verify_totp_code, user_id, code, pending=True
        )
        if not is_valid:
            raise TwoFactorInvalidCodeException()

        # Mark as verified
        totp_repo.mark_verified(pending.id)

        # Enable 2FA on user
        user = user_repo.get_by_id(user_id)
        if user:
            user.totp_enabled = True
            user_repo.flush()

        # Generate backup codes
        backup_codes = backup_repo.generate_backup_codes(user_id)

        user_repo.commit()

        return schemas.TwoFactorVerifySetupResponse(
            enabled=True,
            backup_codes=backup_codes,
        )

    @staticmethod
    def disable_2fa(
        db: Session,
        user: "db_models.User",
        password: str | None = None,
        email_code: str | None = None,
    ) -> schemas.MessageResponse:
        """
        Disable 2FA for user.

        Requires password or email code verification.

        Args:
            db: Database session
            user: Current user
            password: User's password (optional)
            email_code: Email verification code (optional)

        Returns:
            Success message

        Raises:
            TwoFactorNotEnabledException: If 2FA is not enabled
            InvalidCredentialsException: If password/email code is invalid
        """
        from services.email_login_service import EmailLoginService

        if not user.totp_enabled:
            raise TwoFactorNotEnabledException()

        # Verify identity
        if password:
            if not verify_password(password, str(user.hashed_password)):
                from models.exceptions import InvalidCredentialsException

                raise InvalidCredentialsException("Invalid password")
        elif email_code:
            # This will raise an exception if invalid
            EmailLoginService.verify_code(db, str(user.email), email_code)
        else:
            from models.exceptions import ValidationException

            raise ValidationException("Password or email verification code required")

        # Delete TOTP secret and backup codes
        totp_repo = TOTPRepository(db)
        backup_repo = BackupCodeRepository(db)

        totp_repo.delete_user_totp(int(user.id))
        backup_repo.delete_user_codes(int(user.id))

        # Disable flag
        user.totp_enabled = False
        totp_repo.commit()

        return schemas.MessageResponse(
            message="Two-factor authentication has been disabled"
        )

    @staticmethod
    def get_status(db: Session, user_id: int) -> schemas.TwoFactorStatusResponse:
        """
        Get 2FA status for user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            2FA status response

        Raises:
            UserNotFoundException: If user not found
        """
        user_repo = UserRepository(db)
        backup_repo = BackupCodeRepository(db)

        user = user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException("User not found")

        remaining = 0
        if user.totp_enabled:
            remaining = backup_repo.get_remaining_count(user_id)

        return schemas.TwoFactorStatusResponse(
            enabled=bool(user.totp_enabled),
            backup_codes_remaining=remaining,
        )

    @staticmethod
    def create_temp_token(user_id: int) -> str:
        """
        Create temporary token for 2FA verification step.

        This token can only be used with /auth/2fa/verify endpoint.

        Args:
            user_id: User ID

        Returns:
            JWT temp token string
        """
        expires = datetime.now(timezone.utc) + timedelta(
            minutes=settings.TOTP_TEMP_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": str(user_id),
            "purpose": "2fa_verification",
            "exp": expires,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def verify_temp_token(token: str) -> int | None:
        """
        Verify temporary 2FA token.

        Args:
            token: JWT temp token

        Returns:
            User ID if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            if payload.get("purpose") != "2fa_verification":
                return None
            sub = payload.get("sub")
            return int(sub) if sub else None
        except jwt.exceptions.InvalidTokenError:
            return None

    @staticmethod
    def verify_2fa_login(
        db: Session,
        temp_token: str,
        code: str,
        is_backup_code: bool = False,
    ) -> schemas.Token:
        """
        Verify 2FA code and complete login.

        Args:
            db: Database session
            temp_token: Temporary token from initial auth
            code: TOTP code or backup code
            is_backup_code: True if using backup code

        Returns:
            Full access token

        Raises:
            TwoFactorTempTokenExpiredException: If temp token expired/invalid
            TwoFactorNotEnabledException: If 2FA is not enabled
            TwoFactorInvalidCodeException: If code is invalid
        """
        user_id = TOTPService.verify_temp_token(temp_token)
        if not user_id:
            raise TwoFactorTempTokenExpiredException()

        user_repo = UserRepository(db)
        user = user_repo.get_by_id(user_id)

        if not user or not user.totp_enabled:
            raise TwoFactorNotEnabledException()

        # Verify code
        if is_backup_code:
            backup_repo = BackupCodeRepository(db)
            if not backup_repo.verify_and_consume_code(user_id, code):
                raise TwoFactorInvalidCodeException("Invalid backup code")
            backup_repo.commit()
        else:
            totp_repo = TOTPRepository(db)
            is_valid = TOTPService._wrap_config_error(
                totp_repo.verify_totp_code, user_id, code
            )
            if not is_valid:
                raise TwoFactorInvalidCodeException("Invalid authentication code")

            # Update last used
            totp_record = totp_repo.get_user_totp(user_id)
            if totp_record:
                totp_repo.update_last_used(totp_record.id)
            totp_repo.commit()

        # Track login for retention policy (Law 25 Phase 3)
        from services.auth_service import AuthService

        AuthService.update_last_login(db, user)

        # Issue full access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.email)}, expires_delta=access_token_expires
        )
        # nosec B106: "bearer" is OAuth2 token type, not a password
        return schemas.Token(access_token=access_token, token_type="bearer")  # nosec B106

    @staticmethod
    def regenerate_backup_codes(
        db: Session,
        user: "db_models.User",
        password: str | None = None,
        email_code: str | None = None,
    ) -> schemas.BackupCodesResponse:
        """
        Regenerate backup codes.

        Invalidates all existing backup codes.
        Requires password or email code verification.

        Args:
            db: Database session
            user: Current user
            password: User's password (optional)
            email_code: Email verification code (optional)

        Returns:
            New backup codes

        Raises:
            TwoFactorNotEnabledException: If 2FA is not enabled
            InvalidCredentialsException: If password/email code is invalid
        """
        from services.email_login_service import EmailLoginService

        if not user.totp_enabled:
            raise TwoFactorNotEnabledException()

        # Verify identity
        if password:
            if not verify_password(password, str(user.hashed_password)):
                from models.exceptions import InvalidCredentialsException

                raise InvalidCredentialsException("Invalid password")
        elif email_code:
            EmailLoginService.verify_code(db, str(user.email), email_code)
        else:
            from models.exceptions import ValidationException

            raise ValidationException("Password or email verification code required")

        backup_repo = BackupCodeRepository(db)
        codes = backup_repo.generate_backup_codes(int(user.id))

        backup_repo.commit()
        return schemas.BackupCodesResponse(backup_codes=codes)

    @staticmethod
    def get_backup_codes_count(db: Session, user_id: int, totp_enabled: bool) -> int:
        """
        Get count of remaining backup codes for user.

        Args:
            db: Database session
            user_id: User ID
            totp_enabled: Whether user has 2FA enabled

        Returns:
            Number of remaining backup codes

        Raises:
            TwoFactorNotEnabledException: If 2FA is not enabled
        """
        if not totp_enabled:
            raise TwoFactorNotEnabledException()

        backup_repo = BackupCodeRepository(db)
        return backup_repo.get_remaining_count(user_id)

    @staticmethod
    def check_requires_2fa(user: "db_models.User") -> bool:
        """
        Check if user requires 2FA to complete login.

        Args:
            user: User object

        Returns:
            True if 2FA is enabled for this user
        """
        return bool(user.totp_enabled)

    @staticmethod
    def login_with_2fa_check(
        db: Session, email: str, password: str
    ) -> Union[schemas.Token, schemas.TwoFactorRequiredResponse]:
        """
        Login with 2FA check.

        If 2FA is enabled, returns temp token for 2FA verification.
        Otherwise, returns full access token.

        Args:
            db: Database session
            email: User email
            password: User password

        Returns:
            Token or TwoFactorRequiredResponse

        Raises:
            InvalidCredentialsException: If email or password is incorrect
        """
        from authentication.auth import authenticate_user
        from models.exceptions import InvalidCredentialsException

        user = authenticate_user(db, email, password)
        if not user:
            raise InvalidCredentialsException("Incorrect email or password")

        # Check if 2FA is enabled
        if TOTPService.check_requires_2fa(user):
            temp_token = TOTPService.create_temp_token(int(user.id))
            return schemas.TwoFactorRequiredResponse(
                requires_2fa=True,
                temp_token=temp_token,
            )

        # Track login for retention policy (Law 25 Phase 3)
        from services.auth_service import AuthService

        AuthService.update_last_login(db, user)

        # No 2FA - issue full token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.email)}, expires_delta=access_token_expires
        )
        # nosec B106: "bearer" is OAuth2 token type, not a password
        return schemas.Token(access_token=access_token, token_type="bearer")  # nosec B106
