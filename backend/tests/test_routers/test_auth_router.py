"""Integration tests for auth API endpoints."""


class TestAuthRouter:
    """Test cases for /api/auth endpoints."""

    def test_register_new_user(self, client):
        """New user can register with consent fields (Law 25)."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePassword123!",
                "display_name": "New User",
                "accepts_terms": True,
                "accepts_privacy_policy": True,
                "marketing_consent": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"

    def test_register_requires_terms_consent(self, client):
        """Registration fails without terms consent (Law 25)."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePassword123!",
                "display_name": "New User",
                "accepts_terms": False,
                "accepts_privacy_policy": True,
            },
        )

        assert response.status_code == 422
        assert "terms" in response.json()["detail"].lower()

    def test_register_requires_privacy_consent(self, client):
        """Registration fails without privacy consent (Law 25)."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "username": "newuser",
                "password": "SecurePassword123!",
                "display_name": "New User",
                "accepts_terms": True,
                "accepts_privacy_policy": False,
            },
        )

        assert response.status_code == 422
        assert "privacy" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, client, test_user):
        """Cannot register with existing email."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": test_user.email,
                "username": "differentuser",
                "password": "AnotherPassword123!",
                "display_name": "Duplicate User",
                "accepts_terms": True,
                "accepts_privacy_policy": True,
            },
        )

        assert response.status_code == 422
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, client, test_user):
        """Cannot register with existing username."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "different@example.com",
                "username": test_user.username,
                "password": "AnotherPassword123!",
                "display_name": "Duplicate User",
                "accepts_terms": True,
                "accepts_privacy_policy": True,
            },
        )

        assert response.status_code == 422
        assert "username" in response.json()["detail"].lower()

    def test_login_success(self, client, test_user):
        """Valid credentials return token."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "testpassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client, test_user):
        """Invalid password is rejected."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": test_user.email,
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401

    def test_login_invalid_email(self, client):
        """Invalid email is rejected."""
        response = client.post(
            "/api/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "anypassword",
            },
        )

        assert response.status_code == 401

    def test_get_me_requires_auth(self, client):
        """Protected endpoints require valid token."""
        response = client.get("/api/auth/me")

        assert response.status_code == 401

    def test_get_me_with_token(self, client, test_user, auth_headers):
        """Protected endpoints work with valid token."""
        response = client.get("/api/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email

    def test_update_profile(self, client, auth_headers):
        """User can update their profile."""
        response = client.put(
            "/api/auth/profile",
            headers=auth_headers,
            json={"display_name": "Updated Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"

    def test_change_password(self, client, auth_headers):
        """User can change their password."""
        response = client.put(
            "/api/auth/password",
            headers=auth_headers,
            json={
                "current_password": "testpassword123",
                "new_password": "NewPassword456!",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "successfully" in data["message"].lower()

    def test_change_password_wrong_current(self, client, auth_headers):
        """Cannot change password with wrong current password."""
        response = client.put(
            "/api/auth/password",
            headers=auth_headers,
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456",
            },
        )

        assert response.status_code == 422

    def test_get_activity_history(self, client, auth_headers):
        """User can get their activity history."""
        response = client.get("/api/auth/activity", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "ideas_count" in data
        assert "votes_count" in data

    def test_get_consent_status(self, client, auth_headers):
        """User can get their consent status (Law 25)."""
        response = client.get("/api/auth/consent", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "terms_accepted" in data
        assert "privacy_accepted" in data
        assert "marketing_consent" in data
        assert "requires_reconsent" in data

    def test_get_consent_requires_auth(self, client):
        """Consent endpoint requires authentication."""
        response = client.get("/api/auth/consent")

        assert response.status_code == 401

    def test_update_marketing_consent(self, client, auth_headers):
        """User can update marketing consent (Law 25)."""
        # First get current status
        response = client.get("/api/auth/consent", headers=auth_headers)
        assert response.status_code == 200
        initial_consent = response.json()["marketing_consent"]

        # Toggle marketing consent
        response = client.put(
            "/api/auth/consent",
            headers=auth_headers,
            json={"marketing_consent": not initial_consent},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["marketing_consent"] == (not initial_consent)

    def test_update_consent_requires_auth(self, client):
        """Consent update requires authentication."""
        response = client.put(
            "/api/auth/consent",
            json={"marketing_consent": True},
        )

        assert response.status_code == 401
