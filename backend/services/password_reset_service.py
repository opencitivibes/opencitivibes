"""
Password Reset Service with comprehensive security measures.

Security features (addressing audit findings):
- Finding #2 (CRITICAL): Brute-force protection with attempt tracking
- Finding #3 (HIGH): Timing attack mitigation with jitter and dummy hashing
- Finding #6 (HIGH): Password complexity validation
- Finding #9 (MEDIUM): Comprehensive audit logging
- Finding #16: Have I Been Pwned integration (k-anonymity)
- Finding #17: Session invalidation after password reset
"""

import hashlib
import random
import re
import time
from datetime import datetime, timezone
from typing import Optional

import bcrypt
import httpx
from loguru import logger
from sqlalchemy.orm import Session

from models.config import settings
from models.exceptions import (
    PasswordResetAccountLockedException,
    PasswordResetCodeExpiredException,
    PasswordResetCodeInvalidException,
    PasswordResetMaxAttemptsException,
    PasswordResetRateLimitException,
    PasswordResetTokenInvalidException,
    PasswordValidationException,
)
from repositories.password_reset_repository import PasswordResetRepository
from repositories.user_repository import UserRepository
from services.email_service import EmailService

# Common passwords to block (top 100 most common)
COMMON_PASSWORDS = {
    "password",
    "123456",
    "12345678",
    "qwerty",
    "abc123",
    "monkey",
    "1234567",
    "letmein",
    "trustno1",
    "dragon",
    "baseball",
    "iloveyou",
    "master",
    "sunshine",
    "ashley",
    "bailey",
    "shadow",
    "123123",
    "654321",
    "superman",
    "qazwsx",
    "michael",
    "football",
    "password1",
    "password123",
    "welcome",
    "welcome1",
    "admin",
    "admin123",
    "login",
    "passw0rd",
    "starwars",
    "princess",
    "solo",
    "qwerty123",
    "azerty",
    "aaaaaa",
    "666666",
    "888888",
    "000000",
    "1111111",
}


class PasswordResetService:
    """Service for password reset operations with security protections."""

    # Timing attack protection constants
    MIN_RESPONSE_TIME_MS = 800
    MAX_JITTER_MS = 200

    @staticmethod
    def _hash_email_for_logging(email: str) -> str:
        """Hash email for secure logging (don't log full emails)."""
        return hashlib.sha256(email.lower().encode()).hexdigest()[:16]

    @staticmethod
    def _get_monotonic_time_ms() -> float:
        """Get monotonic time in milliseconds for timing measurements."""
        return time.monotonic() * 1000

    @classmethod
    def _ensure_minimum_time(cls, start_time_ms: float) -> None:
        """
        Ensure minimum response time to prevent timing attacks (Finding #3).

        Uses jitter and busy-wait for the final portion to be more precise.
        """
        elapsed = cls._get_monotonic_time_ms() - start_time_ms
        # Non-cryptographic random is fine for timing jitter - just adds unpredictability
        target_time = cls.MIN_RESPONSE_TIME_MS + random.randint(0, cls.MAX_JITTER_MS)  # nosec B311
        remaining = target_time - elapsed

        if remaining > 0:
            # Sleep for most of the remaining time
            if remaining > 50:
                time.sleep((remaining - 50) / 1000)
            # Busy-wait for the final 50ms for precision
            while cls._get_monotonic_time_ms() - start_time_ms < target_time:
                pass

    @staticmethod
    def _perform_dummy_hash() -> None:
        """
        Perform a dummy bcrypt hash to equalize timing (Finding #3).

        Used when user doesn't exist to prevent enumeration via timing.
        """
        # Use a fixed cost factor matching our real hashing
        bcrypt.hashpw(b"dummy_password_for_timing", bcrypt.gensalt(rounds=12))

    @staticmethod
    def validate_password_strength(password: str) -> list[str]:
        """
        Validate password meets complexity requirements (Finding #6).

        Returns list of failed requirements (empty if valid).
        """
        errors: list[str] = []

        # Minimum length
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")

        # Maximum length (prevent DoS)
        if len(password) > 128:
            errors.append("Password must be at most 128 characters long")

        # Require uppercase
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")

        # Require lowercase
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")

        # Require digit
        if not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")

        # Check for common passwords
        if password.lower() in COMMON_PASSWORDS:
            errors.append(
                "Password is too common, please choose a more unique password"
            )

        # Check for sequential patterns (123, abc, etc.)
        if re.search(r"(012|123|234|345|456|567|678|789|890)", password):
            errors.append("Password contains sequential numbers")
        if re.search(
            r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)",
            password.lower(),
        ):
            errors.append("Password contains sequential letters")

        # Check for repeated characters (3+ same char)
        if re.search(r"(.)\1{2,}", password):
            errors.append("Password contains too many repeated characters")

        return errors

    @staticmethod
    def check_password_pwned(password: str, timeout: float = 2.0) -> Optional[int]:
        """
        Check if password has been exposed in data breaches (Finding #16).

        Uses Have I Been Pwned API with k-anonymity model.
        Returns count of times seen in breaches, or None if check failed.
        """
        try:
            # Hash the password with SHA-1 (required by HIBP API - not used for security)
            sha1_hash = (
                hashlib.sha1(password.encode(), usedforsecurity=False)
                .hexdigest()
                .upper()
            )
            prefix = sha1_hash[:5]
            suffix = sha1_hash[5:]

            # Query HIBP API with only the prefix (k-anonymity)
            url = f"https://api.pwnedpasswords.com/range/{prefix}"
            response = httpx.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "OpenCitiVibes-PasswordCheck/1.0"},
            )

            if response.status_code != 200:
                logger.warning(f"HIBP API returned status {response.status_code}")
                return None

            # Search for our suffix in the response
            for line in response.text.splitlines():
                parts = line.split(":")
                if len(parts) == 2 and parts[0] == suffix:
                    return int(parts[1])

            return 0  # Not found in breaches

        except httpx.TimeoutException:
            logger.warning("HIBP API timeout, skipping breach check")
            return None
        except Exception as e:
            logger.warning(f"HIBP API error: {e}")
            return None

    @classmethod
    def request_reset(
        cls,
        db: Session,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        language: str = "en",
    ) -> dict:
        """
        Request a password reset code.

        Returns the same response whether user exists or not (enumeration prevention).

        Args:
            db: Database session
            email: Email address
            ip_address: Client IP for audit logging
            user_agent: Client user agent for audit logging
            language: User's preferred language

        Returns:
            Response dict with message and expires_in_seconds
        """
        start_time = cls._get_monotonic_time_ms()
        email_hash = cls._hash_email_for_logging(email)

        try:
            # Look up user
            user_repo = UserRepository(db)
            user = user_repo.get_by_email(email.lower())

            if user:
                # Check for account lockout (Finding #4)
                repo = PasswordResetRepository(db)
                is_locked, retry_after = repo.check_account_lockout(user.id)

                if is_locked:
                    logger.warning(
                        f"Password reset blocked - account locked: email_hash={email_hash}",
                        ip=ip_address,
                    )
                    raise PasswordResetAccountLockedException(
                        retry_after_seconds=retry_after or 86400
                    )

                # Check rate limit per user
                codes_in_hour = repo.count_codes_in_window(user.id, hours=1)
                if codes_in_hour >= settings.PASSWORD_RESET_CODES_PER_HOUR:
                    logger.warning(
                        f"Password reset rate limited: email_hash={email_hash}",
                        ip=ip_address,
                    )
                    raise PasswordResetRateLimitException(retry_after_seconds=3600)

                # Invalidate any existing tokens
                repo.invalidate_user_tokens(user.id)

                # Create new token
                token, plain_code = repo.create_token(
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                repo.commit()

                # Send email
                display_name = user.display_name or user.email.split("@")[0]
                EmailService.send_password_reset_code(
                    to_email=user.email,
                    code=plain_code,
                    display_name=display_name,
                    language=language,
                    expires_minutes=settings.PASSWORD_RESET_CODE_EXPIRY_MINUTES,
                )

                logger.info(
                    f"Password reset code sent: email_hash={email_hash}",
                    ip=ip_address,
                )
            else:
                # User doesn't exist - perform dummy hash to equalize timing
                cls._perform_dummy_hash()
                logger.info(
                    f"Password reset requested for non-existent email: hash={email_hash}",
                    ip=ip_address,
                )

            return {
                "message": "If this email is registered, you will receive a password reset code shortly.",
                "expires_in_seconds": settings.PASSWORD_RESET_CODE_EXPIRY_MINUTES * 60,
            }

        finally:
            # Ensure consistent timing (Finding #3)
            cls._ensure_minimum_time(start_time)

    @classmethod
    def verify_code(
        cls,
        db: Session,
        email: str,
        code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> dict:
        """
        Verify a password reset code.

        Args:
            db: Database session
            email: Email address
            code: 6-digit verification code
            ip_address: Client IP for context verification
            user_agent: Client user agent for context verification

        Returns:
            Response dict with reset_token and expires_in_seconds

        Raises:
            PasswordResetCodeInvalidException: Invalid code
            PasswordResetCodeExpiredException: Code expired
            PasswordResetMaxAttemptsException: Too many failed attempts
        """
        start_time = cls._get_monotonic_time_ms()
        email_hash = cls._hash_email_for_logging(email)

        try:
            user_repo = UserRepository(db)
            user = user_repo.get_by_email(email.lower())
            if not user:
                cls._perform_dummy_hash()
                logger.warning(
                    f"Code verification for non-existent email: hash={email_hash}",
                    ip=ip_address,
                )
                raise PasswordResetCodeInvalidException()

            repo = PasswordResetRepository(db)

            # Get active code for user
            active_code = repo.get_active_code_for_user(user.id)
            if not active_code:
                logger.warning(
                    f"No active code found for user: email_hash={email_hash}",
                    ip=ip_address,
                )
                raise PasswordResetCodeExpiredException()

            # Check max attempts
            if active_code.attempts >= settings.PASSWORD_RESET_MAX_ATTEMPTS:
                logger.warning(
                    f"Max verification attempts exceeded: email_hash={email_hash}",
                    ip=ip_address,
                )
                raise PasswordResetMaxAttemptsException()

            # Verify the code
            valid_token = repo.get_valid_code(user.id, code)
            if not valid_token:
                # Increment attempts on failure
                repo.increment_attempts(active_code.id)
                repo.commit()

                remaining = (
                    settings.PASSWORD_RESET_MAX_ATTEMPTS - active_code.attempts - 1
                )
                logger.warning(
                    f"Invalid code attempt: email_hash={email_hash}, remaining={remaining}",
                    ip=ip_address,
                )

                if remaining <= 0:
                    raise PasswordResetMaxAttemptsException()
                raise PasswordResetCodeInvalidException()

            # Code is valid - generate reset token
            reset_token = repo.mark_as_verified(valid_token.id)
            repo.commit()

            logger.info(
                f"Password reset code verified: email_hash={email_hash}",
                ip=ip_address,
            )

            return {
                "message": "Code verified. You can now reset your password.",
                "reset_token": reset_token,
                "expires_in_seconds": settings.PASSWORD_RESET_TOKEN_EXPIRY_MINUTES * 60,
            }

        finally:
            cls._ensure_minimum_time(start_time)

    @classmethod
    def reset_password(
        cls,
        db: Session,
        email: str,
        reset_token: str,
        new_password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        language: str = "en",
    ) -> dict:
        """
        Complete password reset with new password.

        Args:
            db: Database session
            email: Email address
            reset_token: Reset token from verification step
            new_password: New password
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            language: User's preferred language

        Returns:
            Response dict with success message

        Raises:
            PasswordResetTokenInvalidException: Invalid or expired token
            PasswordValidationException: Password doesn't meet requirements
        """
        start_time = cls._get_monotonic_time_ms()
        email_hash = cls._hash_email_for_logging(email)

        try:
            user_repo = UserRepository(db)
            user = user_repo.get_by_email(email.lower())
            if not user:
                cls._perform_dummy_hash()
                logger.warning(
                    f"Password reset for non-existent email: hash={email_hash}",
                    ip=ip_address,
                )
                raise PasswordResetTokenInvalidException()

            repo = PasswordResetRepository(db)

            # Verify reset token
            token = repo.get_verified_token(
                reset_token,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            if not token or token.user_id != user.id:
                if token:
                    repo.increment_reset_token_attempts(token.id)
                    repo.commit()
                logger.warning(
                    f"Invalid reset token: email_hash={email_hash}",
                    ip=ip_address,
                )
                raise PasswordResetTokenInvalidException()

            # Validate password strength (Finding #6)
            strength_errors = cls.validate_password_strength(new_password)
            if strength_errors:
                logger.warning(
                    f"Weak password rejected: email_hash={email_hash}",
                    ip=ip_address,
                )
                raise PasswordValidationException(
                    message="Password does not meet security requirements.",
                    requirements=strength_errors,
                )

            # Check if password is breached (Finding #16)
            breach_count = cls.check_password_pwned(new_password)
            if breach_count and breach_count > 0:
                logger.warning(
                    f"Breached password rejected: email_hash={email_hash}, count={breach_count}",
                    ip=ip_address,
                )
                raise PasswordValidationException(
                    message="This password has been exposed in data breaches and cannot be used.",
                    requirements=[
                        f"This password appeared in {breach_count:,} data breaches",
                        "Please choose a different password",
                    ],
                )

            # Hash new password
            from authentication.auth import hash_password

            new_password_hash = hash_password(new_password)

            # Update password and invalidate sessions (Finding #17)
            user_repo.update_password(
                user.id,
                new_password_hash,
                increment_token_version=True,  # Invalidates all sessions
            )

            # Mark token as used
            repo.mark_as_used(token.id)
            repo.commit()

            # Send confirmation email
            display_name = user.display_name or user.email.split("@")[0]
            EmailService.send_password_changed_notification(
                to_email=user.email,
                display_name=display_name,
                changed_at=datetime.now(timezone.utc),
                language=language,
            )

            logger.info(
                f"Password reset completed: email_hash={email_hash}",
                ip=ip_address,
            )

            return {
                "message": "Password has been reset successfully. You can now log in with your new password.",
            }

        finally:
            cls._ensure_minimum_time(start_time)

    @staticmethod
    def cleanup_expired_tokens(db: Session, older_than_hours: int = 24) -> int:
        """
        Clean up expired password reset tokens.

        Should be run periodically via scheduled task.

        Args:
            db: Database session
            older_than_hours: Delete tokens expired more than this many hours ago

        Returns:
            Number of tokens deleted
        """
        repo = PasswordResetRepository(db)
        count = repo.cleanup_expired(older_than_hours=older_than_hours)
        repo.commit()
        logger.info(f"Cleaned up {count} expired password reset tokens")
        return count
