"""
Trusted Device Repository for 2FA Remember Device feature.

Provides CRUD operations for trusted device management.
All IP addresses must be pre-anonymized by the service layer using `anonymize_ip()`.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

import repositories.db_models as db_models

from .base import BaseRepository


class TrustedDeviceRepository(BaseRepository[db_models.TrustedDevice]):
    """Repository for trusted device operations."""

    def __init__(self, db: Session):
        """
        Initialize trusted device repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.TrustedDevice, db)

    def create_trusted_device(
        self,
        user_id: int,
        device_token_hash: str,
        device_fingerprint: str | None,
        device_name: str,
        ip_address_subnet: str | None,
        user_agent: str | None,
        duration_days: int,
    ) -> db_models.TrustedDevice:
        """
        Create a new trusted device record.

        CRITICAL: ip_address_subnet MUST be pre-anonymized by caller using anonymize_ip().

        Args:
            user_id: User ID who owns this device
            device_token_hash: SHA-256 hash of the device token
            device_fingerprint: JSON string with device signals
            device_name: User-friendly device name
            ip_address_subnet: Anonymized IP subnet (Law 25 compliance)
            user_agent: User agent string
            duration_days: Number of days until device trust expires

        Returns:
            Created TrustedDevice record
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=duration_days)

        device = db_models.TrustedDevice(
            user_id=user_id,
            device_token_hash=device_token_hash,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
            ip_address_subnet=ip_address_subnet,
            user_agent=user_agent[:500] if user_agent else None,
            trusted_at=now,
            expires_at=expires_at,
            consent_logged_at=now,
            is_active=True,
        )
        return self.create(device)

    def get_by_token_hash(
        self, device_token_hash: str
    ) -> db_models.TrustedDevice | None:
        """
        Get trusted device by its token hash.

        Args:
            device_token_hash: SHA-256 hash of the device token

        Returns:
            TrustedDevice if found, None otherwise
        """
        return (
            self.db.query(db_models.TrustedDevice)
            .filter(db_models.TrustedDevice.device_token_hash == device_token_hash)
            .first()
        )

    def get_user_devices(
        self,
        user_id: int,
        active_only: bool = True,
    ) -> list[db_models.TrustedDevice]:
        """
        Get all trusted devices for a user.

        Args:
            user_id: User ID
            active_only: If True, only return active (non-revoked) devices

        Returns:
            List of TrustedDevice records
        """
        query = self.db.query(db_models.TrustedDevice).filter(
            db_models.TrustedDevice.user_id == user_id
        )

        if active_only:
            query = query.filter(db_models.TrustedDevice.is_active == True)  # noqa: E712

        return query.order_by(db_models.TrustedDevice.trusted_at.desc()).all()

    def get_user_active_device_count(self, user_id: int) -> int:
        """
        Get count of active trusted devices for a user.

        Args:
            user_id: User ID

        Returns:
            Number of active trusted devices
        """
        return (
            self.db.query(db_models.TrustedDevice)
            .filter(
                db_models.TrustedDevice.user_id == user_id,
                db_models.TrustedDevice.is_active == True,  # noqa: E712
            )
            .count()
        )

    def verify_device_token(
        self,
        user_id: int,
        device_token_hash: str,
    ) -> db_models.TrustedDevice | None:
        """
        Verify if a device token is valid for a user using constant-time comparison.

        SECURITY: Uses hmac.compare_digest() to prevent timing attacks.
        Does NOT use SQL comparison on token hash to avoid timing side-channels.

        Checks:
        - Token exists and belongs to user
        - Device is active (not revoked)
        - Device has not expired

        Args:
            user_id: User ID
            device_token_hash: SHA-256 hash of the device token

        Returns:
            TrustedDevice if valid, None otherwise
        """
        import hmac

        now = datetime.now(timezone.utc)

        # Get all active, non-expired devices for this user
        # Do NOT filter by token_hash in SQL - this prevents timing attacks
        candidates = (
            self.db.query(db_models.TrustedDevice)
            .filter(
                db_models.TrustedDevice.user_id == user_id,
                db_models.TrustedDevice.is_active == True,  # noqa: E712
                db_models.TrustedDevice.expires_at > now,
            )
            .all()
        )

        # Use constant-time comparison for each candidate
        for device in candidates:
            if hmac.compare_digest(device.device_token_hash, device_token_hash):
                return device

        return None

    def update_last_used(self, device_id: int) -> None:
        """
        Update last_used_at timestamp for a device.

        Args:
            device_id: ID of the trusted device
        """
        device = self.get_by_id(device_id)
        if device:
            device.last_used_at = datetime.now(timezone.utc)
            self.flush()

    def update_device_name(self, device_id: int, new_name: str) -> None:
        """
        Update the user-friendly name for a device.

        Args:
            device_id: ID of the trusted device
            new_name: New device name (max 100 chars)
        """
        device = self.get_by_id(device_id)
        if device:
            device.device_name = new_name[:100]
            self.flush()

    def revoke_device(self, device_id: int) -> None:
        """
        Revoke (soft delete) a trusted device.

        Sets is_active=False and records revoked_at timestamp.

        Args:
            device_id: ID of the trusted device to revoke
        """
        device = self.get_by_id(device_id)
        if device:
            device.is_active = False
            device.revoked_at = datetime.now(timezone.utc)
            self.flush()

    def revoke_all_user_devices(self, user_id: int) -> int:
        """
        Revoke all trusted devices for a user.

        Args:
            user_id: User ID

        Returns:
            Number of devices revoked
        """
        now = datetime.now(timezone.utc)
        count = (
            self.db.query(db_models.TrustedDevice)
            .filter(
                db_models.TrustedDevice.user_id == user_id,
                db_models.TrustedDevice.is_active == True,  # noqa: E712
            )
            .update(
                {
                    db_models.TrustedDevice.is_active: False,
                    db_models.TrustedDevice.revoked_at: now,
                },
                synchronize_session=False,
            )
        )
        self.flush()
        return count

    def cleanup_expired_devices(self) -> int:
        """
        Soft-revoke all expired devices.

        Sets is_active=False for devices where expires_at < now and is_active=True.
        This is for scheduled cleanup tasks.

        Returns:
            Number of devices marked as expired
        """
        now = datetime.now(timezone.utc)
        count = (
            self.db.query(db_models.TrustedDevice)
            .filter(
                db_models.TrustedDevice.expires_at < now,
                db_models.TrustedDevice.is_active == True,  # noqa: E712
            )
            .update(
                {
                    db_models.TrustedDevice.is_active: False,
                    db_models.TrustedDevice.revoked_at: now,
                },
                synchronize_session=False,
            )
        )
        self.commit()
        return count

    def delete_old_revoked_devices(self, retention_days: int) -> int:
        """
        Permanently delete revoked devices older than retention period.

        Law 25 compliance: Revoked devices are retained for audit purposes
        for a limited time (default 7 days) then permanently deleted.

        Args:
            retention_days: Number of days to retain revoked devices

        Returns:
            Number of devices permanently deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
        count = (
            self.db.query(db_models.TrustedDevice)
            .filter(
                db_models.TrustedDevice.is_active == False,  # noqa: E712
                db_models.TrustedDevice.revoked_at < cutoff_date,
            )
            .delete(synchronize_session=False)
        )
        self.commit()
        return count

    def get_device_by_user_and_id(
        self,
        user_id: int,
        device_id: int,
    ) -> db_models.TrustedDevice | None:
        """
        Get a device by ID, verifying it belongs to the user.

        Args:
            user_id: User ID (for ownership verification)
            device_id: Device ID

        Returns:
            TrustedDevice if found and owned by user, None otherwise
        """
        return (
            self.db.query(db_models.TrustedDevice)
            .filter(
                db_models.TrustedDevice.id == device_id,
                db_models.TrustedDevice.user_id == user_id,
            )
            .first()
        )
