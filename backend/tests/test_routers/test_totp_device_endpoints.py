"""Integration tests for TOTP device management endpoints."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import repositories.db_models as db_models
from authentication.auth import create_access_token, get_password_hash
from services.trusted_device_service import TrustedDeviceService


@pytest.fixture
def user_with_2fa_and_devices(db_session: Session) -> db_models.User:
    """Create a user with 2FA and some trusted devices."""
    now = datetime.now(timezone.utc)
    user = db_models.User(
        email="device_user@example.com",
        username="deviceuser",
        display_name="Device User",
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
        encrypted_secret="test_secret",
        created_at=now,
        verified_at=now,
    )
    db_session.add(totp_secret)
    db_session.commit()

    return user


@pytest.fixture
def auth_headers_device_user(user_with_2fa_and_devices: db_models.User) -> dict:
    """Get auth headers for device user."""
    token = create_access_token(data={"sub": user_with_2fa_and_devices.email})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def trusted_device(
    db_session: Session, user_with_2fa_and_devices: db_models.User
) -> tuple[str, db_models.TrustedDevice]:
    """Create a trusted device for the user."""
    plain_token, device = TrustedDeviceService.trust_device(
        db=db_session,
        user_id=user_with_2fa_and_devices.id,
        user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/120.0",
        ip_address="192.168.1.100",
        custom_name="Test Device",
        consent_given=True,
    )
    return plain_token, device


class TestListTrustedDevicesEndpoint:
    """Tests for GET /auth/2fa/devices endpoint."""

    def test_list_devices_empty(
        self,
        client: TestClient,
        auth_headers_device_user: dict,
    ) -> None:
        """Test listing devices when none exist."""
        response = client.get("/api/auth/2fa/devices", headers=auth_headers_device_user)

        assert response.status_code == 200
        data = response.json()
        assert data["devices"] == []
        assert data["total"] == 0

    def test_list_devices_with_devices(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_and_devices: db_models.User,
        auth_headers_device_user: dict,
        trusted_device: tuple[str, db_models.TrustedDevice],
    ) -> None:
        """Test listing devices when some exist."""
        response = client.get("/api/auth/2fa/devices", headers=auth_headers_device_user)

        assert response.status_code == 200
        data = response.json()
        assert len(data["devices"]) == 1
        assert data["total"] == 1
        assert data["devices"][0]["device_name"] == "Test Device"
        assert data["devices"][0]["is_active"] is True

    def test_list_devices_unauthorized(self, client: TestClient) -> None:
        """Test that listing devices requires authentication."""
        response = client.get("/api/auth/2fa/devices")
        assert response.status_code == 401


class TestRenameTrustedDeviceEndpoint:
    """Tests for PATCH /auth/2fa/devices/{device_id} endpoint."""

    def test_rename_device_success(
        self,
        client: TestClient,
        db_session: Session,
        auth_headers_device_user: dict,
        trusted_device: tuple[str, db_models.TrustedDevice],
    ) -> None:
        """Test successful device rename."""
        _, device = trusted_device
        response = client.patch(
            f"/api/auth/2fa/devices/{device.id}",
            headers=auth_headers_device_user,
            json={"device_name": "My Home Computer"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["device_name"] == "My Home Computer"
        assert data["id"] == device.id

    def test_rename_device_not_found(
        self,
        client: TestClient,
        auth_headers_device_user: dict,
    ) -> None:
        """Test rename fails for non-existent device."""
        response = client.patch(
            "/api/auth/2fa/devices/99999",
            headers=auth_headers_device_user,
            json={"device_name": "New Name"},
        )

        assert response.status_code == 404

    def test_rename_device_wrong_user(
        self,
        client: TestClient,
        db_session: Session,
        trusted_device: tuple[str, db_models.TrustedDevice],
        other_user: db_models.User,
    ) -> None:
        """Test rename fails for device owned by another user."""
        _, device = trusted_device

        # Create auth headers for other user
        other_token = create_access_token(data={"sub": other_user.email})
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.patch(
            f"/api/auth/2fa/devices/{device.id}",
            headers=other_headers,
            json={"device_name": "Hacker Device"},
        )

        assert response.status_code == 403

    def test_rename_device_unauthorized(
        self,
        client: TestClient,
        trusted_device: tuple[str, db_models.TrustedDevice],
    ) -> None:
        """Test that renaming requires authentication."""
        _, device = trusted_device
        response = client.patch(
            f"/api/auth/2fa/devices/{device.id}",
            json={"device_name": "New Name"},
        )
        assert response.status_code == 401


class TestRevokeTrustedDeviceEndpoint:
    """Tests for DELETE /auth/2fa/devices/{device_id} endpoint."""

    def test_revoke_device_success(
        self,
        client: TestClient,
        db_session: Session,
        auth_headers_device_user: dict,
        trusted_device: tuple[str, db_models.TrustedDevice],
    ) -> None:
        """Test successful device revocation."""
        plain_token, device = trusted_device
        response = client.delete(
            f"/api/auth/2fa/devices/{device.id}",
            headers=auth_headers_device_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert "revoked" in data["message"].lower()

        # Verify device token no longer works
        db_session.expire_all()
        is_valid = TrustedDeviceService.verify_trusted_device(
            db=db_session,
            user_id=device.user_id,
            device_token=plain_token,
        )
        assert is_valid is False

    def test_revoke_device_not_found(
        self,
        client: TestClient,
        auth_headers_device_user: dict,
    ) -> None:
        """Test revoke fails for non-existent device."""
        response = client.delete(
            "/api/auth/2fa/devices/99999",
            headers=auth_headers_device_user,
        )

        assert response.status_code == 404

    def test_revoke_device_wrong_user(
        self,
        client: TestClient,
        db_session: Session,
        trusted_device: tuple[str, db_models.TrustedDevice],
        other_user: db_models.User,
    ) -> None:
        """Test revoke fails for device owned by another user."""
        _, device = trusted_device

        other_token = create_access_token(data={"sub": other_user.email})
        other_headers = {"Authorization": f"Bearer {other_token}"}

        response = client.delete(
            f"/api/auth/2fa/devices/{device.id}",
            headers=other_headers,
        )

        assert response.status_code == 403


class TestRevokeAllTrustedDevicesEndpoint:
    """Tests for DELETE /auth/2fa/devices endpoint."""

    def test_revoke_all_devices_success(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_and_devices: db_models.User,
        auth_headers_device_user: dict,
    ) -> None:
        """Test revoking all devices."""
        # Create multiple devices
        tokens = []
        for i in range(3):
            token, _ = TrustedDeviceService.trust_device(
                db=db_session,
                user_id=user_with_2fa_and_devices.id,
                user_agent=f"Mozilla/{i}",
                ip_address="192.168.1.1",
                custom_name=f"Device {i}",
                consent_given=True,
            )
            tokens.append(token)

        response = client.delete(
            "/api/auth/2fa/devices",
            headers=auth_headers_device_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert "3" in data["message"]

        # Verify all tokens are invalid
        db_session.expire_all()
        for token in tokens:
            is_valid = TrustedDeviceService.verify_trusted_device(
                db=db_session,
                user_id=user_with_2fa_and_devices.id,
                device_token=token,
            )
            assert is_valid is False

    def test_revoke_all_devices_none_exist(
        self,
        client: TestClient,
        auth_headers_device_user: dict,
    ) -> None:
        """Test revoking all devices when none exist."""
        response = client.delete(
            "/api/auth/2fa/devices",
            headers=auth_headers_device_user,
        )

        assert response.status_code == 200
        data = response.json()
        assert "0" in data["message"]

    def test_revoke_all_devices_unauthorized(self, client: TestClient) -> None:
        """Test that revoking all devices requires authentication."""
        response = client.delete("/api/auth/2fa/devices")
        assert response.status_code == 401


class TestVerify2FAWithDeviceTrustEndpoint:
    """Tests for POST /auth/2fa/verify with device trust options."""

    def test_verify_2fa_with_trust_requires_consent(
        self,
        client: TestClient,
        db_session: Session,
        user_with_2fa_and_devices: db_models.User,
    ) -> None:
        """Test that trusting device requires consent."""
        from services.totp_service import TOTPService

        temp_token = TOTPService.create_temp_token(user_with_2fa_and_devices.id)

        # Request with trust_device=True but consent_given=False
        response = client.post(
            "/api/auth/2fa/verify",
            json={
                "temp_token": temp_token,
                "code": "123456",
                "is_backup_code": False,
                "trust_device": True,
                "trust_duration_days": 30,
                "consent_given": False,
            },
        )

        # Should fail with validation error for missing consent
        # Note: This will also fail TOTP verification, but consent check comes first
        assert response.status_code in [400, 401]
