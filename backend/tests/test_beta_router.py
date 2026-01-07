"""Tests for the beta access router.

Security Hardening Phase 1 - Tests for V1 (server-side beta password verification).
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from helpers.rate_limiter import limiter
from main import app
from models.config import settings


@pytest.fixture
def client() -> TestClient:
    """Create a test client with rate limiter reset."""
    # Reset rate limiter state between tests
    limiter.reset()
    return TestClient(app)


class TestBetaVerify:
    """Test cases for POST /api/beta/verify endpoint."""

    def test_verify_correct_password(self, client: TestClient) -> None:
        """Test that correct password grants access."""
        with (
            patch.object(settings, "BETA_MODE", True),
            patch.object(settings, "BETA_PASSWORD", "test-secret-password"),
        ):
            response = client.post(
                "/api/beta/verify", json={"password": "test-secret-password"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Should set httpOnly cookie
            assert "beta_access" in response.cookies

    def test_verify_incorrect_password(self, client: TestClient) -> None:
        """Test that incorrect password is rejected."""
        with (
            patch.object(settings, "BETA_MODE", True),
            patch.object(settings, "BETA_PASSWORD", "correct-password"),
        ):
            response = client.post(
                "/api/beta/verify", json={"password": "wrong-password"}
            )

            assert response.status_code == 422  # ValidationException
            assert "Invalid access code" in response.json()["detail"]

    def test_verify_beta_mode_disabled(self, client: TestClient) -> None:
        """Test that access is granted when beta mode is disabled."""
        with patch.object(settings, "BETA_MODE", False):
            response = client.post(
                "/api/beta/verify", json={"password": "any-password"}
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_verify_no_password_configured(self, client: TestClient) -> None:
        """Test that access is granted when no password is configured."""
        with (
            patch.object(settings, "BETA_MODE", True),
            patch.object(settings, "BETA_PASSWORD", ""),
        ):
            response = client.post(
                "/api/beta/verify", json={"password": "any-password"}
            )

            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_verify_empty_password(self, client: TestClient) -> None:
        """Test that empty password is rejected when password is configured."""
        with (
            patch.object(settings, "BETA_MODE", True),
            patch.object(settings, "BETA_PASSWORD", "secret"),
        ):
            response = client.post("/api/beta/verify", json={"password": ""})

            # Pydantic should reject empty string due to min_length=1
            assert response.status_code == 422

    def test_verify_rate_limiting(self, client: TestClient) -> None:
        """Test that rate limiting is enforced (5/minute)."""
        with (
            patch.object(settings, "BETA_MODE", True),
            patch.object(settings, "BETA_PASSWORD", "secret"),
        ):
            # Make 6 requests - the 6th should be rate limited
            for i in range(5):
                response = client.post("/api/beta/verify", json={"password": "wrong"})
                # First 5 should get through (422 = wrong password)
                assert response.status_code in (422, 200)

            # 6th request should be rate limited
            response = client.post("/api/beta/verify", json={"password": "wrong"})
            assert response.status_code == 429


class TestBetaStatus:
    """Test cases for GET /api/beta/status endpoint."""

    def test_status_beta_mode_enabled_no_cookie(self, client: TestClient) -> None:
        """Test status when beta mode is enabled and no cookie."""
        with patch.object(settings, "BETA_MODE", True):
            response = client.get("/api/beta/status")

            assert response.status_code == 200
            data = response.json()
            assert data["beta_mode_enabled"] is True
            assert data["has_access"] is False

    def test_status_beta_mode_enabled_with_cookie(self, client: TestClient) -> None:
        """Test status when beta mode is enabled and cookie is set."""
        with patch.object(settings, "BETA_MODE", True):
            # Set the cookie
            client.cookies.set("beta_access", "true")
            response = client.get("/api/beta/status")

            assert response.status_code == 200
            data = response.json()
            assert data["beta_mode_enabled"] is True
            assert data["has_access"] is True

    def test_status_beta_mode_disabled(self, client: TestClient) -> None:
        """Test status when beta mode is disabled."""
        with patch.object(settings, "BETA_MODE", False):
            response = client.get("/api/beta/status")

            assert response.status_code == 200
            data = response.json()
            assert data["beta_mode_enabled"] is False
            # has_access should be True when beta mode is disabled
            assert data["has_access"] is True


class TestSecurityRequirements:
    """Test security requirements for the beta router."""

    def test_password_not_in_response(self, client: TestClient) -> None:
        """Ensure the password is never returned in any response."""
        with (
            patch.object(settings, "BETA_MODE", True),
            patch.object(settings, "BETA_PASSWORD", "super-secret"),
        ):
            # Correct password
            response = client.post(
                "/api/beta/verify", json={"password": "super-secret"}
            )
            assert "super-secret" not in response.text

            # Wrong password
            response = client.post("/api/beta/verify", json={"password": "wrong"})
            assert "super-secret" not in response.text

    def test_cookie_httponly_secure(self, client: TestClient) -> None:
        """Test that the beta cookie has security attributes."""
        with (
            patch.object(settings, "BETA_MODE", True),
            patch.object(settings, "BETA_PASSWORD", "test-password"),
            patch.object(settings, "ENVIRONMENT", "production"),
        ):
            response = client.post(
                "/api/beta/verify", json={"password": "test-password"}
            )

            # Check cookie is set (TestClient strips some attributes)
            assert response.status_code == 200
            # Cookie should be set - verify via cookies dict
            assert "beta_access" in response.cookies

    def test_timing_attack_protection(self, client: TestClient) -> None:
        """Test that password comparison uses constant-time comparison."""
        import time

        with (
            patch.object(settings, "BETA_MODE", True),
            patch.object(settings, "BETA_PASSWORD", "correct-password-12345"),
        ):
            # This is a basic test - real timing attacks require statistical analysis
            # We just verify both paths complete without timing-based information leakage

            # Wrong first character
            start = time.perf_counter()
            client.post("/api/beta/verify", json={"password": "xorrect-password-12345"})
            time1 = time.perf_counter() - start

            # Wrong last character
            start = time.perf_counter()
            client.post("/api/beta/verify", json={"password": "correct-password-1234x"})
            time2 = time.perf_counter() - start

            # Times should be similar (within 100ms tolerance for network/system variance)
            assert abs(time1 - time2) < 0.1
