"""Tests for TOTP Service device trust integration."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

import models.schemas as schemas
import repositories.db_models as db_models
from authentication.auth import get_password_hash
from models.exceptions import ValidationException
from services.totp_service import TOTPService
from services.trusted_device_service import TrustedDeviceService


@pytest.fixture
def user_with_2fa(db_session: Session) -> db_models.User:
    """Create a user with 2FA enabled."""
    now = datetime.now(timezone.utc)
    user = db_models.User(
        email="totp_user@example.com",
        username="totpuser",
        display_name="TOTP User",
        hashed_password=get_password_hash("SecurePassword123!"),
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

    # Add TOTP secret
    totp_secret = db_models.UserTOTPSecret(
        user_id=user.id,
        encrypted_secret="test_secret_encrypted",
        created_at=now,
        verified_at=now,
    )
    db_session.add(totp_secret)
    db_session.commit()

    return user


@pytest.fixture
def user_without_2fa(db_session: Session) -> db_models.User:
    """Create a user without 2FA."""
    now = datetime.now(timezone.utc)
    user = db_models.User(
        email="no2fa@example.com",
        username="no2fauser",
        display_name="No 2FA User",
        hashed_password=get_password_hash("SecurePassword123!"),
        is_active=True,
        is_global_admin=False,
        totp_enabled=False,
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


class TestLoginWithDeviceTrust:
    """Tests for login_with_2fa_check_and_device method."""

    def test_login_no_2fa_returns_token(
        self, db_session: Session, user_without_2fa: db_models.User
    ) -> None:
        """Test login without 2FA returns full token."""
        result = TOTPService.login_with_2fa_check_and_device(
            db=db_session,
            email="no2fa@example.com",
            password="SecurePassword123!",
            device_token=None,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert isinstance(result, schemas.Token)
        assert result.access_token is not None
        assert result.token_type == "bearer"

    def test_login_2fa_without_device_token_requires_2fa(
        self, db_session: Session, user_with_2fa: db_models.User
    ) -> None:
        """Test login with 2FA enabled but no device token requires 2FA."""
        result = TOTPService.login_with_2fa_check_and_device(
            db=db_session,
            email="totp_user@example.com",
            password="SecurePassword123!",
            device_token=None,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert isinstance(result, schemas.TwoFactorRequiredResponse)
        assert result.requires_2fa is True
        assert result.temp_token is not None

    def test_login_2fa_with_valid_device_token_bypasses_2fa(
        self, db_session: Session, user_with_2fa: db_models.User
    ) -> None:
        """Test login with valid device token bypasses 2FA."""
        # First, trust the device
        plain_token, _ = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=user_with_2fa.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        # Now login with the device token
        result = TOTPService.login_with_2fa_check_and_device(
            db=db_session,
            email="totp_user@example.com",
            password="SecurePassword123!",
            device_token=plain_token,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert isinstance(result, schemas.Token)
        assert result.access_token is not None

    def test_login_2fa_with_invalid_device_token_requires_2fa(
        self, db_session: Session, user_with_2fa: db_models.User
    ) -> None:
        """Test login with invalid device token still requires 2FA."""
        result = TOTPService.login_with_2fa_check_and_device(
            db=db_session,
            email="totp_user@example.com",
            password="SecurePassword123!",
            device_token="invalid_token_xyz",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert isinstance(result, schemas.TwoFactorRequiredResponse)
        assert result.requires_2fa is True


class TestVerify2FAWithDeviceTrust:
    """Tests for verify_2fa_login with device trust options."""

    @pytest.fixture
    def mock_totp_verify(self):
        """Mock TOTP repository verification to always succeed."""
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "repositories.totp_repository.TOTPRepository.verify_totp_code",
                lambda self, user_id, code: True,
            )
            yield mp

    def test_verify_2fa_without_trust_device(
        self, db_session: Session, user_with_2fa: db_models.User, mock_totp_verify
    ) -> None:
        """Test 2FA verification without trusting device."""
        # Create temp token
        temp_token = TOTPService.create_temp_token(user_with_2fa.id)

        result = TOTPService.verify_2fa_login(
            db=db_session,
            temp_token=temp_token,
            code="123456",
            is_backup_code=False,
            trust_device=False,
        )

        assert isinstance(result, schemas.Token)
        # When trust_device=False, device_token should not be present or be None
        if hasattr(result, "device_token"):
            assert result.device_token is None

    def test_verify_2fa_with_trust_device_requires_consent(
        self, db_session: Session, user_with_2fa: db_models.User, mock_totp_verify
    ) -> None:
        """Test 2FA verification with trust_device requires consent."""
        temp_token = TOTPService.create_temp_token(user_with_2fa.id)

        with pytest.raises(ValidationException) as exc_info:
            TOTPService.verify_2fa_login(
                db=db_session,
                temp_token=temp_token,
                code="123456",
                is_backup_code=False,
                trust_device=True,
                consent_given=False,  # Missing consent
            )

        assert "consent" in str(exc_info.value).lower()

    def test_verify_2fa_with_trust_device_and_consent_returns_device_token(
        self, db_session: Session, user_with_2fa: db_models.User, mock_totp_verify
    ) -> None:
        """Test 2FA verification with trust and consent returns device token."""
        temp_token = TOTPService.create_temp_token(user_with_2fa.id)

        result = TOTPService.verify_2fa_login(
            db=db_session,
            temp_token=temp_token,
            code="123456",
            is_backup_code=False,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            trust_device=True,
            trust_duration_days=14,
            consent_given=True,
        )

        assert isinstance(result, schemas.TokenWithDeviceToken)
        assert result.device_token is not None
        assert result.device_expires_at is not None
        assert result.access_token is not None

    def test_verify_2fa_trust_duration_exceeds_max_still_returns_token(
        self, db_session: Session, user_with_2fa: db_models.User, mock_totp_verify
    ) -> None:
        """Test that invalid trust duration fails silently - auth still succeeds."""
        temp_token = TOTPService.create_temp_token(user_with_2fa.id)

        # Try to trust for 60 days - TrustedDeviceService.trust_device will raise
        # ValidationException, but verify_2fa_login catches it and still returns
        # a valid Token (without device_token)
        result = TOTPService.verify_2fa_login(
            db=db_session,
            temp_token=temp_token,
            code="123456",
            is_backup_code=False,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            trust_device=True,
            trust_duration_days=60,
            consent_given=True,
        )

        # Auth should still succeed, but without device trust
        assert isinstance(result, schemas.Token)
        # Should NOT have device_token since trust failed
        if isinstance(result, schemas.TokenWithDeviceToken):
            assert result.device_token is None


class TestDeviceTrustIntegration:
    """Integration tests for full device trust flow."""

    @pytest.fixture
    def mock_totp_verify(self):
        """Mock TOTP repository verification to always succeed."""
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(
                "repositories.totp_repository.TOTPRepository.verify_totp_code",
                lambda self, user_id, code: True,
            )
            yield mp

    def test_full_trust_and_bypass_flow(
        self, db_session: Session, user_with_2fa: db_models.User, mock_totp_verify
    ) -> None:
        """Test complete flow: login -> 2FA -> trust -> relogin with bypass."""
        # Step 1: Initial login (should require 2FA)
        login_result = TOTPService.login_with_2fa_check_and_device(
            db=db_session,
            email="totp_user@example.com",
            password="SecurePassword123!",
            device_token=None,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        assert isinstance(login_result, schemas.TwoFactorRequiredResponse)
        temp_token = login_result.temp_token

        # Step 2: Verify 2FA and trust device
        verify_result = TOTPService.verify_2fa_login(
            db=db_session,
            temp_token=temp_token,
            code="123456",
            is_backup_code=False,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            trust_device=True,
            consent_given=True,
        )

        assert isinstance(verify_result, schemas.TokenWithDeviceToken)
        device_token = verify_result.device_token

        # Step 3: Re-login with device token (should bypass 2FA)
        relogin_result = TOTPService.login_with_2fa_check_and_device(
            db=db_session,
            email="totp_user@example.com",
            password="SecurePassword123!",
            device_token=device_token,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert isinstance(relogin_result, schemas.Token)
        assert relogin_result.access_token is not None

    def test_revoked_device_requires_2fa_again(
        self, db_session: Session, user_with_2fa: db_models.User
    ) -> None:
        """Test that revoked device requires 2FA again."""
        # Trust device
        plain_token, device = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=user_with_2fa.id,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
            consent_given=True,
        )

        # Verify it works
        result1 = TOTPService.login_with_2fa_check_and_device(
            db=db_session,
            email="totp_user@example.com",
            password="SecurePassword123!",
            device_token=plain_token,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        assert isinstance(result1, schemas.Token)

        # Revoke device
        TrustedDeviceService.revoke_device(
            db=db_session,
            user_id=user_with_2fa.id,
            device_id=device.id,
        )

        # Try to login again with same token (should require 2FA)
        result2 = TOTPService.login_with_2fa_check_and_device(
            db=db_session,
            email="totp_user@example.com",
            password="SecurePassword123!",
            device_token=plain_token,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        assert isinstance(result2, schemas.TwoFactorRequiredResponse)
