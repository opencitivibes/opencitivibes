"""Service layer for email login (magic link) functionality."""

import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import sentry_sdk
from sqlalchemy.orm import Session

from authentication.auth import create_access_token
from models.config import settings
from models.exceptions import (
    EmailDeliveryException,
    EmailLoginCodeExpiredException,
    EmailLoginCodeInvalidException,
    EmailLoginMaxAttemptsException,
    EmailLoginRateLimitException,
    EmailLoginUserNotFoundException,
)
from models.schemas import Token
from repositories.db_models import User
from repositories.email_login_repository import EmailLoginCodeRepository
from repositories.user_repository import UserRepository
from services.email_service import EmailService

logger = logging.getLogger(__name__)


def _hash_email(email: str) -> str:
    """Hash email for privacy-safe logging."""
    return hashlib.sha256(email.lower().encode()).hexdigest()[:8]


class EmailLoginService:
    """Service for handling passwordless email login."""

    @staticmethod
    def _get_active_user(db: Session, email: str) -> User:
        """Get active user by email or raise exception."""
        user_repo = UserRepository(db)
        user = user_repo.get_active_by_email(email)
        if not user:
            raise EmailLoginUserNotFoundException()
        return user

    @staticmethod
    def _check_rate_limit(repo: EmailLoginCodeRepository, user_id: int) -> None:
        """Check rate limit and raise exception if exceeded."""
        codes_count = repo.count_codes_in_window(user_id, hours=1)
        if codes_count >= settings.EMAIL_LOGIN_CODES_PER_HOUR:
            logger.warning(
                "Email login rate limit exceeded",
                extra={"user_id": user_id, "codes_in_window": codes_count},
            )
            raise EmailLoginRateLimitException(
                message="Too many login code requests. Please try again later.",
                retry_after_seconds=3600,
            )

    @staticmethod
    def _send_code_email(
        repo: EmailLoginCodeRepository,
        user: User,
        plain_code: str,
        email: str,
        language: str,
    ) -> None:
        """Send code email and raise exception if delivery fails."""
        display_name = user.display_name or user.username
        success = EmailService.send_login_code(
            to_email=email,
            code=plain_code,
            display_name=display_name,
            language=language,
            expires_minutes=settings.EMAIL_LOGIN_CODE_EXPIRY_MINUTES,
        )
        if not success:
            repo.invalidate_user_codes(user.id)
            logger.error(
                "Email login code delivery failed",
                extra={"user_id": user.id, "email_hash": _hash_email(email)},
            )
            raise EmailDeliveryException()

    @staticmethod
    def _validate_code(
        repo: EmailLoginCodeRepository, db: Session, user_id: int, code: str
    ) -> None:
        """Validate code and track attempts. Raises on invalid code."""
        active_code = repo.get_active_code_for_user(user_id)
        if not active_code:
            raise EmailLoginCodeExpiredException()
        if active_code.attempts >= settings.EMAIL_LOGIN_MAX_ATTEMPTS:
            raise EmailLoginMaxAttemptsException()

        valid_code = repo.get_valid_code(user_id, code)
        if not valid_code:
            # Calculate attempts BEFORE commit (SQLAlchemy expires objects on commit)
            attempts_before = active_code.attempts
            repo.increment_attempts(active_code.id)
            repo.commit()

            # New attempt count is the previous value + 1
            attempts = attempts_before + 1
            remaining = settings.EMAIL_LOGIN_MAX_ATTEMPTS - attempts

            logger.warning(
                "Email login code verification failed",
                extra={"user_id": user_id, "attempts": attempts},
            )

            # Alert on suspicious activity (3+ failed attempts)
            if attempts >= 3:
                sentry_sdk.capture_message(
                    f"Multiple failed email login attempts (user_id={user_id}, attempts={attempts})",
                    level="warning",
                )

            if remaining <= 0:
                raise EmailLoginMaxAttemptsException()
            raise EmailLoginCodeInvalidException(
                f"Invalid code. {remaining} attempts remaining."
            )
        repo.mark_as_used(valid_code.id)

    @staticmethod
    def request_login_code(
        db: Session,
        email: str,
        ip_address: Optional[str] = None,
        language: str = "en",
    ) -> int:
        """Request a login code to be sent to the user's email."""
        user = EmailLoginService._get_active_user(db, email)
        repo = EmailLoginCodeRepository(db)
        EmailLoginService._check_rate_limit(repo, user.id)

        repo.invalidate_user_codes(user.id)
        _, plain_code = repo.create_code(user_id=user.id, ip_address=ip_address)
        EmailLoginService._send_code_email(repo, user, plain_code, email, language)

        repo.commit()

        logger.info(
            "Email login code requested",
            extra={
                "email_hash": _hash_email(email),
                "user_id": user.id,
                "ip_address": ip_address,
            },
        )

        return settings.EMAIL_LOGIN_CODE_EXPIRY_MINUTES * 60

    @staticmethod
    def verify_code(
        db: Session,
        email: str,
        code: str,
        ip_address: Optional[str] = None,
    ) -> Token:
        """Verify a login code and issue JWT token."""
        user = EmailLoginService._get_active_user(db, email)
        repo = EmailLoginCodeRepository(db)

        EmailLoginService._validate_code(repo, db, user.id, code)

        # Track login for retention policy (Law 25 Phase 3)
        from services.auth_service import AuthService

        AuthService.update_last_login(db, user)

        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        repo.commit()

        logger.info(
            "Email login successful",
            extra={
                "email_hash": _hash_email(email),
                "user_id": user.id,
                "ip_address": ip_address,
            },
        )

        return Token(access_token=access_token, token_type="bearer")  # noqa: S106

    @staticmethod
    def check_pending_code(db: Session, email: str) -> Optional[int]:
        """
        Check if user has a pending (active) code.

        Returns:
            Seconds until expiry if active code exists, None otherwise
        """
        user_repo = UserRepository(db)
        user = user_repo.get_active_by_email(email)
        if not user:
            return None

        repo = EmailLoginCodeRepository(db)

        active_code = repo.get_active_code_for_user(user.id)
        if not active_code:
            return None

        # Handle both naive (from DB) and aware (from code) datetimes
        expires_at = active_code.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        remaining = (expires_at - now).total_seconds()

        return max(0, int(remaining))

    @staticmethod
    def cleanup_expired_codes(db: Session, older_than_hours: int = 24) -> int:
        """
        Clean up expired codes.

        Should be called periodically (e.g., hourly cron job).

        Returns:
            Number of codes deleted
        """
        repo = EmailLoginCodeRepository(db)
        count = repo.cleanup_expired(older_than_hours)
        repo.commit()

        if count > 0:
            logger.info("Cleaned up expired email login codes", extra={"count": count})

        return count
