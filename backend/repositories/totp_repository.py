"""Repository for TOTP 2FA operations."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

import pyotp
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from models.config import settings
from repositories.base import BaseRepository
from repositories.db_models import UserBackupCode, UserTOTPSecret


class TOTPRepository(BaseRepository[UserTOTPSecret]):
    """Repository for TOTP secret management."""

    def __init__(self, db: Session):
        """Initialize the repository."""
        super().__init__(UserTOTPSecret, db)
        self._fernet: Optional[Fernet] = None

    def _get_fernet(self) -> Fernet:
        """Get Fernet instance for encryption/decryption.

        Raises:
            ValueError: If TOTP_ENCRYPTION_KEY is not configured or invalid.
        """
        if self._fernet is None:
            if not settings.TOTP_ENCRYPTION_KEY:
                raise ValueError("TOTP_ENCRYPTION_KEY is not configured")
            try:
                self._fernet = Fernet(settings.TOTP_ENCRYPTION_KEY.encode())
            except Exception as e:
                raise ValueError(f"Invalid TOTP_ENCRYPTION_KEY: {e}") from e
        return self._fernet

    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret (32-character base32 string)."""
        return pyotp.random_base32()

    def encrypt_secret(self, secret: str) -> str:
        """Encrypt TOTP secret for database storage."""
        fernet = self._get_fernet()
        return fernet.encrypt(secret.encode()).decode()

    def decrypt_secret(self, encrypted: str) -> str:
        """Decrypt TOTP secret from database.

        Raises:
            ValueError: If decryption fails (invalid token or key mismatch).
        """
        fernet = self._get_fernet()
        try:
            return fernet.decrypt(encrypted.encode()).decode()
        except InvalidToken as e:
            raise ValueError(f"Failed to decrypt TOTP secret: {e}") from e

    def create_totp_secret(self, user_id: int) -> tuple[UserTOTPSecret, str]:
        """
        Create new TOTP secret for user.

        Invalidates any existing unverified secret.

        Returns:
            Tuple of (UserTOTPSecret record, plain text secret)
        """
        # Delete any existing unverified secret for this user
        self.db.query(UserTOTPSecret).filter(
            UserTOTPSecret.user_id == user_id,
            UserTOTPSecret.is_verified == False,  # noqa: E712
        ).delete()

        plain_secret = self.generate_secret()
        encrypted = self.encrypt_secret(plain_secret)

        record = UserTOTPSecret(
            user_id=user_id,
            encrypted_secret=encrypted,
            is_verified=False,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(record)
        self.db.flush()

        return record, plain_secret

    def get_user_totp(self, user_id: int) -> Optional[UserTOTPSecret]:
        """Get user's verified TOTP secret."""
        return (
            self.db.query(UserTOTPSecret)
            .filter(
                UserTOTPSecret.user_id == user_id,
                UserTOTPSecret.is_verified == True,  # noqa: E712
            )
            .first()
        )

    def get_pending_totp(self, user_id: int) -> Optional[UserTOTPSecret]:
        """Get user's pending (unverified) TOTP secret."""
        return (
            self.db.query(UserTOTPSecret)
            .filter(
                UserTOTPSecret.user_id == user_id,
                UserTOTPSecret.is_verified == False,  # noqa: E712
            )
            .first()
        )

    def verify_totp_code(self, user_id: int, code: str, pending: bool = False) -> bool:
        """
        Verify a TOTP code against user's secret.

        Args:
            user_id: User ID
            code: 6-digit TOTP code
            pending: If True, verify against pending (setup) secret

        Returns:
            True if code is valid
        """
        if pending:
            record = self.get_pending_totp(user_id)
        else:
            record = self.get_user_totp(user_id)

        if not record:
            return False

        plain_secret = self.decrypt_secret(record.encrypted_secret)
        totp = pyotp.TOTP(plain_secret)

        # valid_window=1 allows codes from ±30 seconds (handles clock skew)
        return totp.verify(code, valid_window=1)

    def mark_verified(self, totp_id: int) -> None:
        """Mark TOTP secret as verified (setup complete)."""
        self.db.query(UserTOTPSecret).filter(UserTOTPSecret.id == totp_id).update(
            {
                "is_verified": True,
                "verified_at": datetime.now(timezone.utc),
            }
        )
        self.db.flush()

    def update_last_used(self, totp_id: int) -> None:
        """Update last_used_at timestamp."""
        self.db.query(UserTOTPSecret).filter(UserTOTPSecret.id == totp_id).update(
            {"last_used_at": datetime.now(timezone.utc)}
        )
        self.db.flush()

    def delete_user_totp(self, user_id: int) -> int:
        """Delete user's TOTP secret (disable 2FA)."""
        result = (
            self.db.query(UserTOTPSecret)
            .filter(UserTOTPSecret.user_id == user_id)
            .delete()
        )
        self.db.flush()
        return result  # type: ignore[return-value]

    def get_provisioning_uri(self, secret: str, email: str) -> str:
        """
        Generate provisioning URI for QR code.

        Args:
            secret: Plain text TOTP secret
            email: User's email (used as account name)

        Returns:
            otpauth:// URI for QR code generation
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=settings.TOTP_ISSUER_NAME)


class BackupCodeRepository(BaseRepository[UserBackupCode]):
    """Repository for backup code management."""

    CODE_LENGTH = 8  # 8-character alphanumeric codes
    # Use only unambiguous characters (no 0/O, 1/l/I)
    ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # pragma: allowlist secret

    def __init__(self, db: Session):
        """Initialize the repository."""
        super().__init__(UserBackupCode, db)

    def generate_code(self) -> str:
        """Generate a single backup code (8 alphanumeric characters)."""
        return "".join(secrets.choice(self.ALPHABET) for _ in range(self.CODE_LENGTH))

    @staticmethod
    def hash_code(code: str) -> str:
        """Hash backup code for storage."""
        normalized = code.upper().replace("-", "").replace(" ", "")
        return hashlib.sha256(normalized.encode()).hexdigest()

    def generate_backup_codes(self, user_id: int) -> list[str]:
        """
        Generate new set of backup codes for user.

        Invalidates all existing codes.

        Returns:
            List of plain text backup codes (show to user once)
        """
        # Delete existing codes
        self.db.query(UserBackupCode).filter(UserBackupCode.user_id == user_id).delete()

        plain_codes = []
        for _ in range(settings.TOTP_BACKUP_CODE_COUNT):
            code = self.generate_code()
            plain_codes.append(code)

            record = UserBackupCode(
                user_id=user_id,
                code_hash=self.hash_code(code),
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(record)

        self.db.flush()
        return plain_codes

    def verify_and_consume_code(self, user_id: int, code: str) -> bool:
        """
        Verify backup code and mark as used.

        Returns:
            True if code was valid and consumed
        """
        code_hash = self.hash_code(code)

        record = (
            self.db.query(UserBackupCode)
            .filter(
                UserBackupCode.user_id == user_id,
                UserBackupCode.code_hash == code_hash,
                UserBackupCode.used_at.is_(None),
            )
            .first()
        )

        if not record:
            return False

        record.used_at = datetime.now(timezone.utc)
        self.db.flush()
        return True

    def get_remaining_count(self, user_id: int) -> int:
        """Get count of unused backup codes."""
        return (
            self.db.query(UserBackupCode)
            .filter(
                UserBackupCode.user_id == user_id,
                UserBackupCode.used_at.is_(None),
            )
            .count()
        )

    def delete_user_codes(self, user_id: int) -> int:
        """Delete all backup codes for a user."""
        result = (
            self.db.query(UserBackupCode)
            .filter(UserBackupCode.user_id == user_id)
            .delete()
        )
        self.db.flush()
        return result  # type: ignore[return-value]
