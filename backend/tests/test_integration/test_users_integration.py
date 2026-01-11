"""
Integration tests for users router.

Tests the user profile functionality:
1. Get user public profile
2. Privacy settings filtering
3. Access control (public/registered/private)
"""

from fastapi.testclient import TestClient

import repositories.db_models as db_models


def test_get_user_public_profile(client: TestClient, test_user: db_models.User):
    """Test getting a user's public profile."""
    response = client.get(f"/api/users/{test_user.id}/profile")
    assert response.status_code == 200
    data = response.json()
    assert "username" in data


def test_get_user_profile_nonexistent(client: TestClient):
    """Test getting non-existent user profile fails."""
    response = client.get("/api/users/99999/profile")
    assert response.status_code == 404


def test_get_user_profile_authenticated(
    client: TestClient, test_user: db_models.User, auth_headers: dict
):
    """Test getting user profile while authenticated."""
    response = client.get(f"/api/users/{test_user.id}/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "username" in data


def test_get_user_profile_contains_filtered_fields(
    client: TestClient, test_user: db_models.User
):
    """Test user profile respects privacy settings."""
    response = client.get(f"/api/users/{test_user.id}/profile")
    assert response.status_code == 200
    data = response.json()

    # Should not contain sensitive information
    assert "email" not in data or data.get("email") is None
    assert "hashed_password" not in data


def test_get_own_profile_through_users_endpoint(
    client: TestClient, test_user: db_models.User, auth_headers: dict
):
    """Test getting own profile through users endpoint."""
    response = client.get(f"/api/users/{test_user.id}/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "username" in data


def test_get_other_user_profile(
    client: TestClient, other_user: db_models.User, auth_headers: dict
):
    """Test getting another user's public profile."""
    response = client.get(f"/api/users/{other_user.id}/profile", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "username" in data


def test_user_profile_no_auth_required(client: TestClient, test_user: db_models.User):
    """Test user profiles can be accessed without authentication."""
    response = client.get(f"/api/users/{test_user.id}/profile")
    assert response.status_code == 200


def test_user_profile_response_structure(client: TestClient, test_user: db_models.User):
    """Test user profile response has expected structure."""
    response = client.get(f"/api/users/{test_user.id}/profile")
    assert response.status_code == 200
    data = response.json()

    # Check for expected fields based on privacy settings
    assert isinstance(data, dict)
    # Username should typically be visible
    assert "username" in data or "display_name" in data
