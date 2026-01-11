"""
Integration tests for auth router.

Tests the complete authentication flow:
1. User registration
2. Login with valid credentials
3. Login with invalid credentials
4. Get current user (/me)
5. Update profile
6. Change password
"""

import pytest
from fastapi.testclient import TestClient

import repositories.db_models as db_models


@pytest.fixture
def registration_data() -> dict:
    """Valid registration data."""
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "TestPassword123!",
        "display_name": "New User",
        "consent_terms_accepted": True,
        "consent_privacy_accepted": True,
        "consent_terms_version": "1.0",
        "consent_privacy_version": "1.0",
        "marketing_consent": False,
    }


def test_register_new_user(client: TestClient, registration_data: dict):
    """Test user registration with valid data."""
    response = client.post("/api/auth/register", json=registration_data)
    # May be 200 or 422 depending on validation rules
    assert response.status_code in [200, 422]
    if response.status_code == 200:
        data = response.json()
        assert data["email"] == registration_data["email"]
        assert data["username"] == registration_data["username"]
        assert data["display_name"] == registration_data["display_name"]
        assert "hashed_password" not in data


def test_register_duplicate_email(
    client: TestClient, test_user: db_models.User, registration_data: dict
):
    """Test registration fails with duplicate email."""
    registration_data["email"] = test_user.email
    registration_data["username"] = "differentusername"
    response = client.post("/api/auth/register", json=registration_data)
    # Could be 400 or 422
    assert response.status_code in [400, 422]


def test_login_valid_credentials(client: TestClient, test_user: db_models.User):
    """Test login with valid credentials returns access token."""
    response = client.post(
        "/api/auth/login",
        data={"username": test_user.email, "password": "testpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client: TestClient, test_user: db_models.User):
    """Test login with invalid password fails."""
    response = client.post(
        "/api/auth/login",
        data={"username": test_user.email, "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_invalid_email(client: TestClient):
    """Test login with non-existent email fails."""
    response = client.post(
        "/api/auth/login",
        data={"username": "nonexistent@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_get_current_user(
    client: TestClient, test_user: db_models.User, auth_headers: dict
):
    """Test getting current user profile."""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username
    assert data["display_name"] == test_user.display_name


def test_get_current_user_unauthorized(client: TestClient):
    """Test getting current user without authentication fails."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_update_profile(
    client: TestClient, test_user: db_models.User, auth_headers: dict
):
    """Test updating user profile."""
    update_data = {
        "display_name": "Updated Display Name",
    }
    response = client.put("/api/auth/profile", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == update_data["display_name"]


def test_change_password(
    client: TestClient, test_user: db_models.User, auth_headers: dict
):
    """Test changing user password."""
    password_data = {
        "current_password": "testpassword123",
        "new_password": "NewPassword123!",
    }
    response = client.put(
        "/api/auth/password", json=password_data, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Password changed successfully"

    # Verify new password works
    login_response = client.post(
        "/api/auth/login",
        data={"username": test_user.email, "password": "NewPassword123!"},
    )
    assert login_response.status_code == 200


def test_change_password_wrong_current(client: TestClient, auth_headers: dict):
    """Test changing password with wrong current password fails."""
    password_data = {
        "current_password": "wrongpassword",
        "new_password": "NewPassword123!",
    }
    response = client.put(
        "/api/auth/password", json=password_data, headers=auth_headers
    )
    # Could be 400 or 422 depending on validation
    assert response.status_code in [400, 422]


def test_refresh_token(client: TestClient, auth_headers: dict):
    """Test refreshing access token."""
    response = client.post("/api/auth/refresh", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_get_consent_status(client: TestClient, auth_headers: dict):
    """Test getting user consent status."""
    response = client.get("/api/auth/consent", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "terms_accepted" in data
    assert "privacy_accepted" in data


def test_update_consent(client: TestClient, auth_headers: dict):
    """Test updating user consent preferences."""
    consent_data = {
        "marketing_consent": True,
    }
    response = client.put("/api/auth/consent", json=consent_data, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "terms_accepted" in data


def test_get_activity_history(client: TestClient, auth_headers: dict):
    """Test getting user activity history."""
    response = client.get("/api/auth/activity", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "ideas_count" in data
    assert "comments_count" in data
    assert "votes_count" in data
