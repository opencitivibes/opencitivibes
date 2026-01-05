"""Repository for email login code operations."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.config import settings
from repositories.base import BaseRepository
from repositories.db_models import EmailLoginCode


class EmailLoginCodeRepository(BaseRepository[EmailLoginCode]):
    """Repository for managing email login codes."""

    def __init__(self, db: Session):
        """Initialize the repository."""
        super().__init__(EmailLoginCode, db)

    @staticmethod
    def generate_code() -> str:
        """Generate a random numeric code of configured length."""
        max_value = 10**settings.EMAIL_LOGIN_CODE_LENGTH
        code_int = secrets.randbelow(max_value)
        return str(code_int).zfill(settings.EMAIL_LOGIN_CODE_LENGTH)

    @staticmethod
    def hash_code(code: str) -> str:
        """Hash a code using SHA-256."""
        return hashlib.sha256(code.encode()).hexdigest()

    def create_code(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
    ) -> tuple[EmailLoginCode, str]:
        """
        Create a new login code for a user.

        Returns:
            Tuple of (EmailLoginCode model, plain_text_code)
        """
        plain_code = self.generate_code()
        code_hash = self.hash_code(plain_code)

        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.EMAIL_LOGIN_CODE_EXPIRY_MINUTES
        )

        code_record = EmailLoginCode(
            user_id=user_id,
            code_hash=code_hash,
            expires_at=expires_at,
            ip_address=ip_address,
        )

        self.db.add(code_record)
        self.db.flush()

        return code_record, plain_code

    def get_valid_code(self, user_id: int, code: str) -> Optional[EmailLoginCode]:
        """
        Get a valid (not expired, not used, not max attempts) code for user.

        Args:
            user_id: The user's ID
            code: The plain text code to verify

        Returns:
            EmailLoginCode if valid, None otherwise
        """
        code_hash = self.hash_code(code)
        now = datetime.now(timezone.utc)

        return (
            self.db.query(EmailLoginCode)
            .filter(
                and_(
                    EmailLoginCode.user_id == user_id,
                    EmailLoginCode.code_hash == code_hash,
                    EmailLoginCode.expires_at > now,
                    EmailLoginCode.used_at.is_(None),
                    EmailLoginCode.attempts < settings.EMAIL_LOGIN_MAX_ATTEMPTS,
                )
            )
            .first()
        )

    def increment_attempts(self, code_id: int) -> None:
        """Increment the attempt counter for a code."""
        self.db.query(EmailLoginCode).filter(EmailLoginCode.id == code_id).update(
            {EmailLoginCode.attempts: EmailLoginCode.attempts + 1}
        )
        self.db.flush()

    def mark_as_used(self, code_id: int) -> None:
        """Mark a code as successfully used."""
        self.db.query(EmailLoginCode).filter(EmailLoginCode.id == code_id).update(
            {EmailLoginCode.used_at: datetime.now(timezone.utc)}
        )
        self.db.flush()

    def invalidate_user_codes(self, user_id: int) -> int:
        """
        Invalidate all unused codes for a user (when new code is requested).

        Returns:
            Number of codes invalidated
        """
        now = datetime.now(timezone.utc)
        result = (
            self.db.query(EmailLoginCode)
            .filter(
                and_(
                    EmailLoginCode.user_id == user_id,
                    EmailLoginCode.used_at.is_(None),
                    EmailLoginCode.expires_at > now,
                )
            )
            .update({EmailLoginCode.expires_at: now})
        )
        self.db.flush()
        return result  # type: ignore[return-value]

    def count_codes_in_window(self, user_id: int, hours: int = 1) -> int:
        """
        Count how many codes were created for a user in the time window.

        Used for rate limiting.
        """
        window_start = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = (
            self.db.query(func.count(EmailLoginCode.id))
            .filter(
                and_(
                    EmailLoginCode.user_id == user_id,
                    EmailLoginCode.created_at >= window_start,
                )
            )
            .scalar()
        )
        return result or 0

    def cleanup_expired(self, older_than_hours: int = 24) -> int:
        """
        Delete expired codes older than specified hours.

        Should be run periodically via scheduled task.

        Returns:
            Number of codes deleted
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)

        result = (
            self.db.query(EmailLoginCode)
            .filter(EmailLoginCode.expires_at < cutoff)
            .delete()
        )

        self.db.flush()
        return result  # type: ignore[return-value]

    def get_active_code_for_user(self, user_id: int) -> Optional[EmailLoginCode]:
        """
        Get the most recent active (not expired, not used) code for a user.

        Used to check if user already has a pending code.
        """
        now = datetime.now(timezone.utc)

        return (
            self.db.query(EmailLoginCode)
            .filter(
                and_(
                    EmailLoginCode.user_id == user_id,
                    EmailLoginCode.expires_at > now,
                    EmailLoginCode.used_at.is_(None),
                    EmailLoginCode.attempts < settings.EMAIL_LOGIN_MAX_ATTEMPTS,
                )
            )
            .order_by(EmailLoginCode.created_at.desc())
            .first()
        )
