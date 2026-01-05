"""Integration tests for email login API."""

from unittest.mock import patch

from repositories.email_login_repository import EmailLoginCodeRepository


class TestEmailLoginAPI:
    """Integration tests for email login endpoints."""

    @patch("services.email_login_service.EmailService.send_login_code")
    def test_request_endpoint(self, mock_send, client, db_session, test_user):
        """POST /auth/email-login/request should send code."""
        mock_send.return_value = True

        response = client.post(
            "/api/auth/email-login/request", json={"email": test_user.email}
        )

        assert response.status_code == 200
        data = response.json()
        assert "expires_in_seconds" in data
        assert data["expires_in_seconds"] > 0

    def test_request_endpoint_unknown_email(self, client):
        """POST /auth/email-login/request should fail for unknown email."""
        response = client.post(
            "/api/auth/email-login/request", json={"email": "unknown@example.com"}
        )

        assert response.status_code == 400
        # Error message: "No account found with this email address."
        assert "no account found" in response.json()["detail"].lower()

    def test_request_endpoint_invalid_email(self, client):
        """POST /auth/email-login/request should validate email format."""
        response = client.post(
            "/api/auth/email-login/request", json={"email": "not-an-email"}
        )

        assert response.status_code == 422  # Validation error

    def test_verify_endpoint_success(self, client, db_session, test_user):
        """POST /auth/email-login/verify should return token."""
        # Create code directly
        repo = EmailLoginCodeRepository(db_session)
        _, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        response = client.post(
            "/api/auth/email-login/verify",
            json={"email": test_user.email, "code": plain_code},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_verify_endpoint_wrong_code(self, client, db_session, test_user):
        """POST /auth/email-login/verify should reject wrong code."""
        # Create code
        repo = EmailLoginCodeRepository(db_session)
        repo.create_code(test_user.id)
        db_session.commit()

        response = client.post(
            "/api/auth/email-login/verify",
            json={"email": test_user.email, "code": "000000"},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_verify_endpoint_code_format_validation_non_numeric(
        self, client, test_user
    ):
        """POST /auth/email-login/verify should reject non-numeric code."""
        response = client.post(
            "/api/auth/email-login/verify",
            json={"email": test_user.email, "code": "abcdef"},
        )
        assert response.status_code == 422

    def test_verify_endpoint_code_format_validation_too_short(self, client, test_user):
        """POST /auth/email-login/verify should reject too short code."""
        response = client.post(
            "/api/auth/email-login/verify",
            json={"email": test_user.email, "code": "12345"},
        )
        assert response.status_code == 422

    def test_verify_endpoint_code_format_validation_too_long(self, client, test_user):
        """POST /auth/email-login/verify should reject too long code."""
        response = client.post(
            "/api/auth/email-login/verify",
            json={"email": test_user.email, "code": "1234567"},
        )
        assert response.status_code == 422

    def test_status_endpoint_has_pending(self, client, db_session, test_user):
        """GET /auth/email-login/status should return pending status."""
        # Create code
        repo = EmailLoginCodeRepository(db_session)
        repo.create_code(test_user.id)
        db_session.commit()

        response = client.get(f"/api/auth/email-login/status?email={test_user.email}")

        assert response.status_code == 200
        data = response.json()
        assert data["has_pending_code"] is True
        assert data["expires_in_seconds"] > 0

    def test_status_endpoint_no_code(self, client, test_user):
        """GET /auth/email-login/status should return no pending."""
        response = client.get(f"/api/auth/email-login/status?email={test_user.email}")

        assert response.status_code == 200
        data = response.json()
        assert data["has_pending_code"] is False

    @patch("services.email_login_service.EmailService.send_login_code")
    def test_full_flow(self, mock_send, client, db_session, test_user):
        """Test complete email login flow."""
        mock_send.return_value = True

        # 1. Request code
        response = client.post(
            "/api/auth/email-login/request", json={"email": test_user.email}
        )
        assert response.status_code == 200

        # 2. Get the code from database (simulating receiving email)
        repo = EmailLoginCodeRepository(db_session)
        active_code = repo.get_active_code_for_user(test_user.id)
        assert active_code is not None

        # Create a new code we know for testing
        _, plain_code = repo.create_code(test_user.id)
        db_session.commit()

        # 3. Verify code
        response = client.post(
            "/api/auth/email-login/verify",
            json={"email": test_user.email, "code": plain_code},
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        # 4. Use token to access protected endpoint
        response = client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == test_user.email

    @patch("services.email_login_service.EmailService.send_login_code")
    def test_request_stores_ip(self, mock_send, client, db_session, test_user):
        """Request should store client IP address."""
        mock_send.return_value = True

        # TestClient doesn't set X-Forwarded-For by default
        response = client.post(
            "/api/auth/email-login/request",
            json={"email": test_user.email},
            headers={"X-Forwarded-For": "203.0.113.50"},
        )

        assert response.status_code == 200

        # Check IP was stored
        repo = EmailLoginCodeRepository(db_session)
        active = repo.get_active_code_for_user(test_user.id)
        assert active is not None
        assert active.ip_address == "203.0.113.50"

    @patch("services.email_login_service.EmailService.send_login_code")
    def test_request_uses_accept_language(
        self, mock_send, client, db_session, test_user
    ):
        """Request should use Accept-Language header."""
        mock_send.return_value = True

        response = client.post(
            "/api/auth/email-login/request",
            json={"email": test_user.email},
            headers={"Accept-Language": "fr-CA,fr;q=0.9,en;q=0.8"},
        )

        assert response.status_code == 200
        # Verify French language was used
        call_args = mock_send.call_args
        assert call_args.kwargs["language"] == "fr"

    def test_verify_endpoint_unknown_email(self, client):
        """POST /auth/email-login/verify should fail for unknown email."""
        response = client.post(
            "/api/auth/email-login/verify",
            json={"email": "unknown@example.com", "code": "123456"},
        )

        assert response.status_code == 400
        # Error message: "No account found with this email address."
        assert "no account found" in response.json()["detail"].lower()

    def test_status_endpoint_unknown_email(self, client):
        """GET /auth/email-login/status should return no pending for unknown email."""
        response = client.get("/api/auth/email-login/status?email=unknown@example.com")

        assert response.status_code == 200
        data = response.json()
        assert data["has_pending_code"] is False
