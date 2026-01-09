"""Tests for TrustedDeviceService."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

import repositories.db_models as db_models
from models.exceptions import (
    InsufficientPermissionsException,
    TrustedDeviceLimitExceededException,
    TrustedDeviceNotFoundException,
    ValidationException,
)
from services.trusted_device_service import TrustedDeviceService


class TestTrustedDeviceServiceTokenGeneration:
    """Tests for token generation and hashing methods."""

    def test_generate_device_token_length(self) -> None:
        """Test that generated tokens have appropriate length."""
        token = TrustedDeviceService.generate_device_token()
        # URL-safe base64 encoding of 32 bytes is ~43 chars
        assert len(token) >= 40
        assert len(token) <= 50

    def test_generate_device_token_uniqueness(self) -> None:
        """Test that generated tokens are unique."""
        tokens = [TrustedDeviceService.generate_device_token() for _ in range(100)]
        assert len(set(tokens)) == 100

    def test_hash_device_token_deterministic(self) -> None:
        """Test that hashing is deterministic."""
        token = "test_token_123"
        hash1 = TrustedDeviceService.hash_device_token(token)
        hash2 = TrustedDeviceService.hash_device_token(token)
        assert hash1 == hash2

    def test_hash_device_token_format(self) -> None:
        """Test that hash is proper SHA-256 hex digest."""
        token = "test_token"
        hash_value = TrustedDeviceService.hash_device_token(token)
        # SHA-256 produces 64 hex characters
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_verify_token_hash_constant_time_valid(self) -> None:
        """Test constant-time verification with valid token."""
        token = "test_token_abc"
        expected_hash = TrustedDeviceService.hash_device_token(token)
        assert TrustedDeviceService.verify_token_hash_constant_time(
            token, expected_hash
        )

    def test_verify_token_hash_constant_time_invalid(self) -> None:
        """Test constant-time verification with invalid token."""
        token = "test_token_abc"
        wrong_hash = TrustedDeviceService.hash_device_token("wrong_token")
        assert not TrustedDeviceService.verify_token_hash_constant_time(
            token, wrong_hash
        )


class TestTrustedDeviceServiceFingerprint:
    """Tests for device fingerprint creation."""

    def test_create_device_fingerprint_with_user_agent(self) -> None:
        """Test fingerprint creation with user agent."""
        user_agent = "Mozilla/5.0 (Windows NT 10.0) Chrome/120.0"
        fingerprint = TrustedDeviceService.create_device_fingerprint(
            user_agent=user_agent, ip_address=None
        )
        assert "user_agent_raw" in fingerprint
        assert fingerprint.get("browser") == "Chrome"
        assert fingerprint.get("os") == "Windows 10"
        assert fingerprint.get("platform") == "desktop"

    def test_create_device_fingerprint_with_ip(self) -> None:
        """Test fingerprint creation with IP address."""
        fingerprint = TrustedDeviceService.create_device_fingerprint(
            user_agent=None, ip_address="192.168.1.100"
        )
        # IP should be anonymized to subnet
        assert fingerprint.get("ip_subnet") == "192.168.1.0"

    def test_create_device_fingerprint_mobile(self) -> None:
        """Test fingerprint creation for mobile device."""
        user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0) AppleWebKit/605.1"
        fingerprint = TrustedDeviceService.create_device_fingerprint(
            user_agent=user_agent, ip_address=None
        )
        assert fingerprint.get("platform") == "mobile"
        assert fingerprint.get("os") == "iOS"

    def test_create_device_fingerprint_empty(self) -> None:
        """Test fingerprint creation with no data."""
        fingerprint = TrustedDeviceService.create_device_fingerprint(
            user_agent=None, ip_address=None
        )
        assert "created_at" in fingerprint


class TestTrustedDeviceServiceDeviceName:
    """Tests for device name generation."""

    def test_generate_device_name_chrome_windows(self) -> None:
        """Test device name for Chrome on Windows."""
        user_agent = "Mozilla/5.0 (Windows NT 10.0) Chrome/120.0"
        name = TrustedDeviceService.generate_device_name(user_agent)
        assert name == "Chrome on Windows 10"

    def test_generate_device_name_firefox_macos(self) -> None:
        """Test device name for Firefox on macOS."""
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Firefox/120.0"
        name = TrustedDeviceService.generate_device_name(user_agent)
        assert name == "Firefox on macOS"

    def test_generate_device_name_safari_iphone(self) -> None:
        """Test device name for Safari on iPhone."""
        user_agent = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0) Safari/604.1"
        name = TrustedDeviceService.generate_device_name(user_agent)
        assert name == "Safari on iOS"

    def test_generate_device_name_empty_agent(self) -> None:
        """Test device name with empty user agent."""
        name = TrustedDeviceService.generate_device_name(None)
        assert name == "Unknown Device"

    def test_generate_device_name_unknown_browser(self) -> None:
        """Test device name with unknown browser."""
        user_agent = "SomeRandomBrowser/1.0"
        name = TrustedDeviceService.generate_device_name(user_agent)
        assert "Unknown" in name


class TestTrustedDeviceServiceTrustDevice:
    """Tests for trust_device method."""

    def test_trust_device_success(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test successful device trust creation."""
        plain_token, device = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0 Chrome/120.0",
            ip_address="192.168.1.100",
            duration_days=30,
            consent_given=True,
        )

        assert plain_token is not None
        assert len(plain_token) > 40
        assert device.user_id == test_user.id
        assert device.is_active is True
        assert device.device_name == "Chrome on Unknown OS"

    def test_trust_device_without_consent_fails(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test that trust fails without explicit consent."""
        with pytest.raises(ValidationException) as exc_info:
            TrustedDeviceService.trust_device(
                db=db_session,
                user_id=test_user.id,
                user_agent="Mozilla/5.0",
                ip_address="192.168.1.1",
                consent_given=False,
            )
        assert "consent" in str(exc_info.value).lower()

    def test_trust_device_duration_exceeds_max(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test that duration exceeding max is rejected."""
        with pytest.raises(ValidationException) as exc_info:
            TrustedDeviceService.trust_device(
                db=db_session,
                user_id=test_user.id,
                user_agent="Mozilla/5.0",
                ip_address="192.168.1.1",
                duration_days=31,  # Max is 30
                consent_given=True,
            )
        assert "30 days" in str(exc_info.value)

    def test_trust_device_duration_zero_fails(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test that zero duration is rejected."""
        with pytest.raises(ValidationException) as exc_info:
            TrustedDeviceService.trust_device(
                db=db_session,
                user_id=test_user.id,
                user_agent="Mozilla/5.0",
                ip_address="192.168.1.1",
                duration_days=0,
                consent_given=True,
            )
        assert "at least 1 day" in str(exc_info.value)

    def test_trust_device_with_custom_name(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test device trust with custom name."""
        _, device = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            custom_name="My Home Computer",
            consent_given=True,
        )
        assert device.device_name == "My Home Computer"

    def test_trust_device_max_limit_reached(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test that max device limit is enforced."""
        # Create max devices (default is 5)
        from models.config import settings

        for i in range(settings.TOTP_MAX_TRUSTED_DEVICES_PER_USER):
            TrustedDeviceService.trust_device(
                db=db_session,
                user_id=test_user.id,
                user_agent=f"Mozilla/{i}",
                ip_address="192.168.1.1",
                consent_given=True,
            )

        with pytest.raises(TrustedDeviceLimitExceededException):
            TrustedDeviceService.trust_device(
                db=db_session,
                user_id=test_user.id,
                user_agent="Mozilla/Extra",
                ip_address="192.168.1.1",
                consent_given=True,
            )


class TestTrustedDeviceServiceVerify:
    """Tests for verify_trusted_device method."""

    def test_verify_trusted_device_valid(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test verification of valid trusted device."""
        plain_token, _ = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        is_valid = TrustedDeviceService.verify_trusted_device(
            db=db_session,
            user_id=test_user.id,
            device_token=plain_token,
        )
        assert is_valid is True

    def test_verify_trusted_device_invalid_token(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test verification with invalid token."""
        TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        is_valid = TrustedDeviceService.verify_trusted_device(
            db=db_session,
            user_id=test_user.id,
            device_token="invalid_token_xyz",
        )
        assert is_valid is False

    def test_verify_trusted_device_wrong_user(
        self, db_session: Session, test_user: db_models.User, other_user: db_models.User
    ) -> None:
        """Test verification fails for wrong user."""
        plain_token, _ = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        is_valid = TrustedDeviceService.verify_trusted_device(
            db=db_session,
            user_id=other_user.id,
            device_token=plain_token,
        )
        assert is_valid is False


class TestTrustedDeviceServiceManagement:
    """Tests for device management methods."""

    def test_get_user_devices(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test getting user's devices."""
        # Create two devices
        TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            custom_name="Device 1",
            consent_given=True,
        )
        TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/6.0",
            ip_address="192.168.1.2",
            custom_name="Device 2",
            consent_given=True,
        )

        devices = TrustedDeviceService.get_user_devices(db_session, test_user.id)
        assert len(devices) == 2

    def test_rename_device_success(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test successful device rename."""
        _, device = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        updated = TrustedDeviceService.rename_device(
            db=db_session,
            user_id=test_user.id,
            device_id=device.id,
            new_name="My New Name",
        )
        assert updated.device_name == "My New Name"

    def test_rename_device_not_found(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test rename fails for non-existent device."""
        with pytest.raises(TrustedDeviceNotFoundException):
            TrustedDeviceService.rename_device(
                db=db_session,
                user_id=test_user.id,
                device_id=99999,
                new_name="New Name",
            )

    def test_rename_device_wrong_user(
        self, db_session: Session, test_user: db_models.User, other_user: db_models.User
    ) -> None:
        """Test rename fails for device owned by another user."""
        _, device = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        with pytest.raises(InsufficientPermissionsException):
            TrustedDeviceService.rename_device(
                db=db_session,
                user_id=other_user.id,
                device_id=device.id,
                new_name="New Name",
            )

    def test_revoke_device_success(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test successful device revocation."""
        plain_token, device = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        TrustedDeviceService.revoke_device(
            db=db_session,
            user_id=test_user.id,
            device_id=device.id,
        )

        # Verify device is no longer valid
        is_valid = TrustedDeviceService.verify_trusted_device(
            db=db_session,
            user_id=test_user.id,
            device_token=plain_token,
        )
        assert is_valid is False

    def test_revoke_device_not_found(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test revoke fails for non-existent device."""
        with pytest.raises(TrustedDeviceNotFoundException):
            TrustedDeviceService.revoke_device(
                db=db_session,
                user_id=test_user.id,
                device_id=99999,
            )

    def test_revoke_device_wrong_user(
        self, db_session: Session, test_user: db_models.User, other_user: db_models.User
    ) -> None:
        """Test revoke fails for device owned by another user."""
        _, device = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=test_user.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        with pytest.raises(InsufficientPermissionsException):
            TrustedDeviceService.revoke_device(
                db=db_session,
                user_id=other_user.id,
                device_id=device.id,
            )

    def test_revoke_all_devices(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test revoking all devices."""
        # Create multiple devices
        tokens = []
        for i in range(3):
            token, _ = TrustedDeviceService.trust_device(
                db=db_session,
                user_id=test_user.id,
                user_agent=f"Mozilla/{i}",
                ip_address="192.168.1.1",
                consent_given=True,
            )
            tokens.append(token)

        count = TrustedDeviceService.revoke_all_devices(db_session, test_user.id)
        assert count == 3

        # Verify all tokens are invalid
        for token in tokens:
            is_valid = TrustedDeviceService.verify_trusted_device(
                db=db_session,
                user_id=test_user.id,
                device_token=token,
            )
            assert is_valid is False


class TestTrustedDeviceServiceCleanup:
    """Tests for cleanup methods."""

    def test_cleanup_expired_devices(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test cleanup of expired devices."""
        from repositories.trusted_device_repository import TrustedDeviceRepository

        # Create a device with past expiry
        repo = TrustedDeviceRepository(db_session)
        device = repo.create_trusted_device(
            user_id=test_user.id,
            device_token_hash="expired_hash_123",
            device_fingerprint=None,
            device_name="Expired Device",
            ip_address_subnet=None,
            user_agent=None,
            duration_days=1,
        )
        # Manually set expiry to past
        device.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()

        count = TrustedDeviceService.cleanup_expired_devices(db_session)
        assert count == 1

    def test_delete_old_revoked_devices(
        self, db_session: Session, test_user: db_models.User
    ) -> None:
        """Test deletion of old revoked devices."""
        from repositories.trusted_device_repository import TrustedDeviceRepository

        repo = TrustedDeviceRepository(db_session)
        device = repo.create_trusted_device(
            user_id=test_user.id,
            device_token_hash="old_revoked_hash",
            device_fingerprint=None,
            device_name="Old Revoked",
            ip_address_subnet=None,
            user_agent=None,
            duration_days=30,
        )
        # Revoke and set old revoked_at
        device.is_active = False
        device.revoked_at = datetime.now(timezone.utc) - timedelta(days=10)
        db_session.commit()

        count = TrustedDeviceService.delete_old_revoked_devices(db_session)
        assert count == 1
