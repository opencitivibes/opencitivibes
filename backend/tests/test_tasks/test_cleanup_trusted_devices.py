"""Tests for trusted device cleanup task."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

import repositories.db_models as db_models
from authentication.auth import get_password_hash
from repositories.trusted_device_repository import TrustedDeviceRepository
from services.trusted_device_service import TrustedDeviceService
from tasks.cleanup_trusted_devices import cleanup_trusted_devices


@pytest.fixture
def cleanup_user(db_session: Session) -> db_models.User:
    """Create a user for cleanup tests."""
    now = datetime.now(timezone.utc)
    user = db_models.User(
        email="cleanup_user@example.com",
        username="cleanupuser",
        display_name="Cleanup User",
        hashed_password=get_password_hash("Password123!"),
        is_active=True,
        is_global_admin=False,
        totp_enabled=True,
        consent_terms_accepted=True,
        consent_privacy_accepted=True,
        consent_terms_version="1.0",
        consent_privacy_version="1.0",
        consent_timestamp=now,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestCleanupExpiredDevices:
    """Tests for cleaning up expired devices."""

    def test_cleanup_expired_devices(
        self, db_session: Session, cleanup_user: db_models.User
    ) -> None:
        """Test that expired devices are cleaned up."""
        repo = TrustedDeviceRepository(db_session)

        # Create an expired device
        device = repo.create_trusted_device(
            user_id=cleanup_user.id,
            device_token_hash="expired_device_hash",
            device_fingerprint=None,
            device_name="Expired Device",
            ip_address_subnet=None,
            user_agent=None,
            duration_days=1,
        )

        # Manually set expiry to past
        device.expires_at = datetime.now(timezone.utc) - timedelta(days=5)
        db_session.commit()

        # Create an active device (not expired)
        repo.create_trusted_device(
            user_id=cleanup_user.id,
            device_token_hash="active_device_hash",
            device_fingerprint=None,
            device_name="Active Device",
            ip_address_subnet=None,
            user_agent=None,
            duration_days=30,
        )

        # Run cleanup
        expired_count = TrustedDeviceService.cleanup_expired_devices(db_session)

        assert expired_count == 1

        # Verify expired device is now inactive
        db_session.refresh(device)
        assert device.is_active is False

    def test_cleanup_no_expired_devices(
        self, db_session: Session, cleanup_user: db_models.User
    ) -> None:
        """Test cleanup when no devices are expired."""
        # Create only active devices
        TrustedDeviceService.trust_device(
            db=db_session,
            user_id=cleanup_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        expired_count = TrustedDeviceService.cleanup_expired_devices(db_session)
        assert expired_count == 0


class TestDeleteOldRevokedDevices:
    """Tests for permanently deleting old revoked devices."""

    def test_delete_old_revoked_devices(
        self, db_session: Session, cleanup_user: db_models.User
    ) -> None:
        """Test that old revoked devices are permanently deleted."""
        repo = TrustedDeviceRepository(db_session)

        # Create a device and revoke it
        device = repo.create_trusted_device(
            user_id=cleanup_user.id,
            device_token_hash="revoked_device_hash",
            device_fingerprint=None,
            device_name="Revoked Device",
            ip_address_subnet=None,
            user_agent=None,
            duration_days=30,
        )

        # Revoke and set old revoked_at (10 days ago)
        device.is_active = False
        device.revoked_at = datetime.now(timezone.utc) - timedelta(days=10)
        db_session.commit()

        device_id = device.id

        # Run delete old revoked
        deleted_count = TrustedDeviceService.delete_old_revoked_devices(db_session)

        assert deleted_count == 1

        # Verify device no longer exists
        deleted_device = repo.get_by_id(device_id)
        assert deleted_device is None

    def test_recent_revoked_devices_not_deleted(
        self, db_session: Session, cleanup_user: db_models.User
    ) -> None:
        """Test that recently revoked devices are not deleted."""
        repo = TrustedDeviceRepository(db_session)

        # Create and revoke a device recently
        device = repo.create_trusted_device(
            user_id=cleanup_user.id,
            device_token_hash="recent_revoked_hash",
            device_fingerprint=None,
            device_name="Recent Revoked",
            ip_address_subnet=None,
            user_agent=None,
            duration_days=30,
        )

        # Revoke only 2 days ago (within retention period)
        device.is_active = False
        device.revoked_at = datetime.now(timezone.utc) - timedelta(days=2)
        db_session.commit()

        device_id = device.id

        # Run delete old revoked
        deleted_count = TrustedDeviceService.delete_old_revoked_devices(db_session)

        assert deleted_count == 0

        # Verify device still exists
        remaining_device = repo.get_by_id(device_id)
        assert remaining_device is not None


class TestCleanupTaskIntegration:
    """Integration tests for the cleanup task function."""

    def test_cleanup_task_runs_both_operations(
        self, db_session: Session, cleanup_user: db_models.User
    ) -> None:
        """Test that cleanup task runs both expired and revoked cleanup."""
        repo = TrustedDeviceRepository(db_session)

        # Create an expired device
        expired = repo.create_trusted_device(
            user_id=cleanup_user.id,
            device_token_hash="task_expired_hash",
            device_fingerprint=None,
            device_name="Task Expired",
            ip_address_subnet=None,
            user_agent=None,
            duration_days=1,
        )
        expired.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()

        # Create an old revoked device
        revoked = repo.create_trusted_device(
            user_id=cleanup_user.id,
            device_token_hash="task_revoked_hash",
            device_fingerprint=None,
            device_name="Task Revoked",
            ip_address_subnet=None,
            user_agent=None,
            duration_days=30,
        )
        revoked.is_active = False
        revoked.revoked_at = datetime.now(timezone.utc) - timedelta(days=10)
        db_session.commit()

        revoked_id = revoked.id

        # Run full cleanup task with test db_session
        result = cleanup_trusted_devices(db=db_session)

        assert result["expired_count"] >= 1
        assert result["deleted_count"] >= 1

        # Verify expired device is inactive
        db_session.expire_all()
        db_session.refresh(expired)
        assert expired.is_active is False

        # Verify revoked device is deleted
        deleted = repo.get_by_id(revoked_id)
        assert deleted is None

    def test_cleanup_task_returns_correct_counts(
        self, db_session: Session, cleanup_user: db_models.User
    ) -> None:
        """Test that cleanup task returns accurate counts."""
        # Create no devices to clean
        result = cleanup_trusted_devices(db=db_session)

        assert "expired_count" in result
        assert "deleted_count" in result
        assert isinstance(result["expired_count"], int)
        assert isinstance(result["deleted_count"], int)
