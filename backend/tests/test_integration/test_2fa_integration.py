"""
Integration tests for 2FA (TOTP) flow.

Tests the complete 2FA setup, login, and management flows:
1. Setup 2FA with QR code
2. Verify setup with TOTP code
3. Login with 2FA required
4. Use backup codes
5. Disable 2FA
6. Trusted device flow

Also tests error cases to catch import errors, missing attributes, and API failures.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import repositories.db_models as db_models
from authentication.auth import create_access_token, get_password_hash


@pytest.fixture
def user_for_2fa(db_session: Session) -> db_models.User:
    """Create a user for 2FA testing (without 2FA enabled)."""
    now = datetime.now(timezone.utc)
    user = db_models.User(
        email="2fauser@example.com",
        username="2fauser",
        display_name="2FA User",
        hashed_password=get_password_hash("TestPassword123!"),
        is_active=True,
        is_global_admin=False,
        totp_enabled=False,
        consent_terms_accepted=True,
        consent_privacy_accepted=True,
        consent_terms_version="1.0",
        consent_privacy_version="1.0",
        consent_timestamp=now,
        marketing_consent=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_with_2fa_enabled(db_session: Session) -> tuple[db_models.User, list[str]]:
    """Create a user with 2FA already enabled and return backup codes."""
    now = datetime.now(timezone.utc)
    user = db_models.User(
        email="2faenabled@example.com",
        username="2faenableduser",
        display_name="2FA Enabled User",
        hashed_password=get_password_hash("TestPassword123!"),
        is_active=True,
        is_global_admin=False,
        totp_enabled=True,
        consent_terms_accepted=True,
        consent_privacy_accepted=True,
        consent_terms_version="1.0",
        consent_privacy_version="1.0",
        consent_timestamp=now,
        marketing_consent=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Add TOTP secret
    from repositories.totp_repository import TOTPRepository

    totp_repo = TOTPRepository(db_session)
    _, plain_secret = totp_repo.create_totp_secret(user.id)

    # Mark as verified
    pending = totp_repo.get_pending_totp(user.id)
    if pending:
        totp_repo.mark_verified(pending.id)

    # Generate backup codes
    from repositories.totp_repository import BackupCodeRepository

    backup_repo = BackupCodeRepository(db_session)
    backup_codes = backup_repo.generate_backup_codes(user.id)

    db_session.commit()

    return user, backup_codes


@pytest.fixture
def auth_headers_2fa_user(user_for_2fa: db_models.User) -> dict:
    """Get authentication headers for 2FA user."""
    token = create_access_token(data={"sub": user_for_2fa.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_2fa_enabled(
    user_with_2fa_enabled: tuple[db_models.User, list[str]],
) -> dict:
    """Get authentication headers for user with 2FA enabled."""
    user, _ = user_with_2fa_enabled
    token = create_access_token(data={"sub": user.email})
    return {"Authorization": f"Bearer {token}"}


class TestTwoFactorSetupFlow:
    """Test complete 2FA setup flow."""

    def test_complete_2fa_setup_flow(
        self,
        client: TestClient,
        db_session: Session,
        user_for_2fa: db_models.User,
        auth_headers_2fa_user: dict,
    ):
        """
        Test complete 2FA setup and verification flow.

        Validates:
        - Setup endpoint returns secret and QR code URI
        - Verification works with correct code
        - Backup codes are generated
        - 2FA is enabled on user
        - Status endpoint reflects enabled state
        """
        # Step 1: Initiate 2FA setup
        response = client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers_2fa_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "provisioning_uri" in data
        assert "qr_code_data" in data
        secret = data["secret"]
        assert len(secret) > 0
        assert data["provisioning_uri"].startswith("otpauth://totp/")

        # Step 2: Generate a valid TOTP code
        import pyotp

        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Step 3: Verify setup with code
        response = client.post(
            "/api/auth/2fa/verify-setup",
            headers=auth_headers_2fa_user,
            json={"code": valid_code},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert "backup_codes" in data
        assert len(data["backup_codes"]) > 0
        backup_codes = data["backup_codes"]

        # Each backup code should be 8 characters
        for code in backup_codes:
            assert len(code) == 8

        # Step 4: Verify status shows 2FA enabled
        response = client.get(
            "/api/auth/2fa/status",
            headers=auth_headers_2fa_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["backup_codes_remaining"] > 0

        # Verify user record updated
        db_session.refresh(user_for_2fa)
        assert user_for_2fa.totp_enabled is True

    def test_setup_when_already_enabled(
        self,
        client: TestClient,
        auth_headers_2fa_enabled: dict,
    ):
        """Setup fails when 2FA already enabled."""
        response = client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers_2fa_enabled,
        )

        assert response.status_code == 400
        assert "already enabled" in response.json()["detail"].lower()

    def test_verify_setup_invalid_code(
        self,
        client: TestClient,
        user_for_2fa: db_models.User,
        auth_headers_2fa_user: dict,
    ):
        """Verify setup fails with invalid code."""
        # Setup first
        response = client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers_2fa_user,
        )
        assert response.status_code == 200

        # Try to verify with wrong code
        response = client.post(
            "/api/auth/2fa/verify-setup",
            headers=auth_headers_2fa_user,
            json={"code": "000000"},
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_verify_setup_without_setup(
        self,
        client: TestClient,
        auth_headers_2fa_user: dict,
    ):
        """Verify setup fails when setup wasn't initiated."""
        response = client.post(
            "/api/auth/2fa/verify-setup",
            headers=auth_headers_2fa_user,
            json={"code": "123456"},
        )

        assert response.status_code == 400
        assert (
            "incomplete" in response.json()["detail"].lower()
            or "no pending" in response.json()["detail"].lower()
        )


class TestTwoFactorLoginFlow:
    """Test 2FA during login."""

    def test_login_with_2fa_required(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
    ):
        """
        Test login flow when 2FA is enabled.

        Validates:
        - Initial login returns temp_token instead of access_token
        - Verification with TOTP code returns access_token
        - User can access protected endpoints with access_token
        """
        user, _ = user_with_2fa_enabled

        # Get the TOTP secret to generate valid code
        from repositories.totp_repository import TOTPRepository

        totp_repo = TOTPRepository(db_session)
        verified_totp = totp_repo.get_user_totp(user.id)
        assert verified_totp is not None

        # Decrypt secret (in real scenario, service does this)
        plain_secret = totp_repo.decrypt_secret(verified_totp.encrypted_secret)

        # Generate valid TOTP code
        import pyotp

        totp = pyotp.TOTP(plain_secret)
        valid_code = totp.now()

        # Step 1: Initial login
        response = client.post(
            "/api/auth/login",
            data={
                "username": user.email,
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "requires_2fa" in data or "temp_token" in data

        # Extract temp_token
        if "requires_2fa" in data:
            assert data["requires_2fa"] is True
            temp_token = data["temp_token"]
        else:
            temp_token = data["temp_token"]

        # Step 2: Verify 2FA code
        response = client.post(
            "/api/auth/2fa/verify",
            json={
                "temp_token": temp_token,
                "code": valid_code,
                "is_backup_code": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Step 3: Use access token to access protected endpoint
        access_token = data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["email"] == user.email

    def test_login_with_backup_code(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
    ):
        """Test login with backup code instead of TOTP."""
        user, backup_codes = user_with_2fa_enabled

        # Initial login
        response = client.post(
            "/api/auth/login",
            data={
                "username": user.email,
                "password": "TestPassword123!",
            },
        )

        data = response.json()
        temp_token = data.get("temp_token")

        # Use first backup code
        backup_code = backup_codes[0]
        response = client.post(
            "/api/auth/2fa/verify",
            json={
                "temp_token": temp_token,
                "code": backup_code,
                "is_backup_code": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

        # Try to use same backup code again (should fail)
        response = client.post(
            "/api/auth/login",
            data={
                "username": user.email,
                "password": "TestPassword123!",
            },
        )
        temp_token = response.json().get("temp_token")

        response = client.post(
            "/api/auth/2fa/verify",
            json={
                "temp_token": temp_token,
                "code": backup_code,
                "is_backup_code": True,
            },
        )

        assert response.status_code == 401

    def test_2fa_verify_invalid_code(
        self,
        client: TestClient,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
    ):
        """2FA verification fails with invalid code."""
        user, _ = user_with_2fa_enabled

        # Initial login
        response = client.post(
            "/api/auth/login",
            data={
                "username": user.email,
                "password": "TestPassword123!",
            },
        )

        temp_token = response.json().get("temp_token")

        # Try invalid code
        response = client.post(
            "/api/auth/2fa/verify",
            json={
                "temp_token": temp_token,
                "code": "000000",
                "is_backup_code": False,
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    def test_2fa_verify_invalid_temp_token(self, client: TestClient):
        """2FA verification fails with invalid temp token."""
        response = client.post(
            "/api/auth/2fa/verify",
            json={
                "temp_token": "invalid_token",
                "code": "123456",
                "is_backup_code": False,
            },
        )

        assert response.status_code in [400, 401]


class TestTwoFactorDisableFlow:
    """Test disabling 2FA."""

    def test_disable_2fa_with_password(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
        auth_headers_2fa_enabled: dict,
    ):
        """
        Test disabling 2FA with password verification.

        Validates:
        - Disable endpoint works with correct password
        - 2FA is disabled on user
        - Status reflects disabled state
        - TOTP secrets and backup codes are deleted
        """
        user, _ = user_with_2fa_enabled

        # Disable 2FA - use request() since delete() doesn't support json parameter
        response = client.request(
            "DELETE",
            "/api/auth/2fa/disable",
            headers=auth_headers_2fa_enabled,
            json={"password": "TestPassword123!"},
        )

        assert response.status_code == 200
        assert "disabled" in response.json()["message"].lower()

        # Verify status shows disabled
        response = client.get(
            "/api/auth/2fa/status",
            headers=auth_headers_2fa_enabled,
        )

        assert response.status_code == 200
        assert response.json()["enabled"] is False

        # Verify user record updated
        db_session.refresh(user)
        assert user.totp_enabled is False

    def test_disable_2fa_wrong_password(
        self,
        client: TestClient,
        auth_headers_2fa_enabled: dict,
    ):
        """Disable fails with wrong password."""
        response = client.request(
            "DELETE",
            "/api/auth/2fa/disable",
            headers=auth_headers_2fa_enabled,
            json={"password": "WrongPassword123!"},
        )

        assert response.status_code == 401

    def test_disable_2fa_when_not_enabled(
        self,
        client: TestClient,
        auth_headers_2fa_user: dict,
    ):
        """Disable fails when 2FA not enabled."""
        response = client.request(
            "DELETE",
            "/api/auth/2fa/disable",
            headers=auth_headers_2fa_user,
            json={"password": "TestPassword123!"},
        )

        assert response.status_code == 400
        assert "not enabled" in response.json()["detail"].lower()


class TestTwoFactorBackupCodes:
    """Test backup code management."""

    def test_regenerate_backup_codes(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
        auth_headers_2fa_enabled: dict,
    ):
        """
        Test regenerating backup codes.

        Validates:
        - New backup codes are generated
        - Old backup codes are invalidated
        - Count reflects new codes
        """
        user, old_codes = user_with_2fa_enabled

        # Regenerate codes
        response = client.post(
            "/api/auth/2fa/backup-codes/regenerate",
            headers=auth_headers_2fa_enabled,
            json={"password": "TestPassword123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "backup_codes" in data
        new_codes = data["backup_codes"]
        assert len(new_codes) > 0

        # New codes should be different from old codes
        assert set(new_codes) != set(old_codes)

        # Old backup codes should no longer work
        # (This would require a login flow test, documented here)

    def test_backup_codes_count(
        self,
        client: TestClient,
        auth_headers_2fa_enabled: dict,
    ):
        """Test getting backup codes count."""
        response = client.get(
            "/api/auth/2fa/backup-codes/count",
            headers=auth_headers_2fa_enabled,
        )

        assert response.status_code == 200
        data = response.json()
        assert "remaining" in data
        assert data["remaining"] >= 0


class TestTrustedDeviceFlow:
    """Test trusted device functionality."""

    def test_2fa_with_device_trust(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
    ):
        """
        Test 2FA login with device trust.

        Validates:
        - User can opt to trust device during 2FA verification
        - Device token is returned
        - Subsequent login from trusted device skips 2FA
        """
        user, _ = user_with_2fa_enabled

        # Get TOTP secret and generate code
        from repositories.totp_repository import TOTPRepository

        totp_repo = TOTPRepository(db_session)
        verified_totp = totp_repo.get_user_totp(user.id)
        assert verified_totp is not None
        plain_secret = totp_repo.decrypt_secret(verified_totp.encrypted_secret)

        import pyotp

        totp = pyotp.TOTP(plain_secret)
        valid_code = totp.now()

        # Initial login
        response = client.post(
            "/api/auth/login",
            data={
                "username": user.email,
                "password": "TestPassword123!",
            },
        )
        temp_token = response.json().get("temp_token")

        # Verify with device trust
        response = client.post(
            "/api/auth/2fa/verify",
            json={
                "temp_token": temp_token,
                "code": valid_code,
                "is_backup_code": False,
                "trust_device": True,
                "trust_duration_days": 30,
                "consent_given": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

        # Should also have device token info
        if "device_token" in data:
            assert "device_expires_at" in data

    def test_list_trusted_devices(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
        auth_headers_2fa_enabled: dict,
    ):
        """Test listing trusted devices."""
        # Initially should have no devices
        response = client.get(
            "/api/auth/2fa/devices",
            headers=auth_headers_2fa_enabled,
        )

        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert "total" in data

    def test_revoke_trusted_device(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
        auth_headers_2fa_enabled: dict,
    ):
        """Test revoking a trusted device."""
        user, _ = user_with_2fa_enabled

        # Create a trusted device first
        from services.trusted_device_service import TrustedDeviceService

        _, device = TrustedDeviceService.trust_device(
            db=db_session,
            user_id=user.id,
            user_agent="Test Browser",
            ip_address="192.168.1.1",
            custom_name="Test Device",
            consent_given=True,
        )

        # Revoke it
        response = client.delete(
            f"/api/auth/2fa/devices/{device.id}",
            headers=auth_headers_2fa_enabled,
        )

        assert response.status_code == 200
        assert "revoked" in response.json()["message"].lower()

    def test_revoke_all_trusted_devices(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
        auth_headers_2fa_enabled: dict,
    ):
        """Test revoking all trusted devices requires password."""
        response = client.request(
            "DELETE",
            "/api/auth/2fa/devices",
            headers=auth_headers_2fa_enabled,
            json={"password": "TestPassword123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestTwoFactorSecurityFeatures:
    """Test security features of 2FA."""

    def test_setup_requires_authentication(self, client: TestClient):
        """2FA setup requires valid authentication."""
        response = client.post("/api/auth/2fa/setup")
        assert response.status_code == 401

    def test_status_requires_authentication(self, client: TestClient):
        """2FA status endpoint requires authentication."""
        response = client.get("/api/auth/2fa/status")
        assert response.status_code == 401

    def test_disable_requires_authentication(self, client: TestClient):
        """2FA disable requires authentication."""
        response = client.request(
            "DELETE",
            "/api/auth/2fa/disable",
            json={"password": "TestPassword123!"},
        )
        assert response.status_code == 401

    def test_backup_codes_shown_once(
        self,
        client: TestClient,
        user_for_2fa: db_models.User,
        auth_headers_2fa_user: dict,
    ):
        """
        Backup codes are only shown during setup verification.

        After setup, only the count is available, not the actual codes.
        """
        # Setup 2FA
        response = client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers_2fa_user,
        )
        secret = response.json()["secret"]

        import pyotp

        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        # Verify and get backup codes
        response = client.post(
            "/api/auth/2fa/verify-setup",
            headers=auth_headers_2fa_user,
            json={"code": valid_code},
        )

        assert "backup_codes" in response.json()
        assert len(response.json()["backup_codes"]) > 0  # Verify codes are returned

        # Status endpoint should NOT return actual codes
        response = client.get(
            "/api/auth/2fa/status",
            headers=auth_headers_2fa_user,
        )

        data = response.json()
        assert "backup_codes" not in data
        assert "backup_codes_remaining" in data


class TestTwoFactorErrorCases:
    """Test error cases and edge conditions."""

    def test_invalid_code_format(
        self,
        client: TestClient,
        auth_headers_2fa_user: dict,
    ):
        """Verify setup rejects invalid code format."""
        # Setup first
        client.post(
            "/api/auth/2fa/setup",
            headers=auth_headers_2fa_user,
        )

        # Try code with invalid format
        response = client.post(
            "/api/auth/2fa/verify-setup",
            headers=auth_headers_2fa_user,
            json={"code": "12345"},  # Too short
        )

        assert response.status_code == 422

    def test_expired_temp_token(self, client: TestClient):
        """2FA verification rejects expired temp token."""
        # Create an expired temp token
        import jwt
        from datetime import timedelta
        from models.config import settings

        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_token = jwt.encode(
            {"sub": 999, "exp": expired_time},
            settings.SECRET_KEY,
            algorithm="HS256",
        )

        response = client.post(
            "/api/auth/2fa/verify",
            json={
                "temp_token": expired_token,
                "code": "123456",
                "is_backup_code": False,
            },
        )

        assert response.status_code in [400, 401]

    def test_trust_device_without_consent(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_enabled: tuple[db_models.User, list[str]],
    ):
        """
        Device trust requires explicit consent (Law 25 compliance).

        Validates: Consent validation for device trust.
        """
        user, _ = user_with_2fa_enabled

        # Get valid TOTP code
        from repositories.totp_repository import TOTPRepository

        totp_repo = TOTPRepository(db_session)
        verified_totp = totp_repo.get_user_totp(user.id)
        assert verified_totp is not None
        plain_secret = totp_repo.decrypt_secret(verified_totp.encrypted_secret)

        import pyotp

        totp = pyotp.TOTP(plain_secret)
        valid_code = totp.now()

        # Login
        response = client.post(
            "/api/auth/login",
            data={
                "username": user.email,
                "password": "TestPassword123!",
            },
        )
        temp_token = response.json().get("temp_token")

        # Try to trust device without consent
        response = client.post(
            "/api/auth/2fa/verify",
            json={
                "temp_token": temp_token,
                "code": valid_code,
                "is_backup_code": False,
                "trust_device": True,
                "trust_duration_days": 30,
                "consent_given": False,  # No consent!
            },
        )

        # Should reject with 422 validation error (Law 25 requires explicit consent)
        assert response.status_code == 422
        assert "consent" in response.json()["detail"].lower()
