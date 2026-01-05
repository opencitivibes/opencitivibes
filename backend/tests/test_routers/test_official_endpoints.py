"""Integration tests for official role endpoints."""

from datetime import datetime, timezone

import pytest

import repositories.db_models as db_models
from authentication.auth import create_access_token, get_password_hash


@pytest.fixture
def official_user(db_session) -> db_models.User:
    """Create a user with official status."""
    user = db_models.User(
        email="official@example.com",
        username="officialuser",
        display_name="Official User",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_global_admin=False,
        is_official=True,
        official_title="City Planner",
        official_verified_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def requesting_user(db_session) -> db_models.User:
    """Create a user who requested official status."""
    user = db_models.User(
        email="requesting@example.com",
        username="requestinguser",
        display_name="Requesting User",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        is_global_admin=False,
        requests_official_status=True,
        official_title_request="Community Leader",
        official_request_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def official_auth_headers(official_user) -> dict:
    """Get authentication headers for official user."""
    token = create_access_token(data={"sub": official_user.email})
    return {"Authorization": f"Bearer {token}"}


class TestListOfficials:
    """Tests for GET /admin/officials."""

    def test_list_officials_success(self, client, admin_auth_headers, official_user):
        """Test listing officials as admin."""
        response = client.get(
            "/api/admin/officials",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == official_user.id
        assert data[0]["official_title"] == "City Planner"

    def test_list_officials_unauthorized(self, client, auth_headers):
        """Test that non-admins cannot list officials."""
        response = client.get(
            "/api/admin/officials",
            headers=auth_headers,
        )

        assert response.status_code == 403

    def test_list_officials_unauthenticated(self, client):
        """Test that unauthenticated users cannot list officials."""
        response = client.get("/api/admin/officials")

        assert response.status_code == 401


class TestGrantOfficialStatus:
    """Tests for POST /admin/officials/grant."""

    def test_grant_official_success(self, client, admin_auth_headers, test_user):
        """Test granting official status."""
        response = client.post(
            "/api/admin/officials/grant",
            headers=admin_auth_headers,
            json={
                "user_id": test_user.id,
                "official_title": "Urban Planner",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_official"] is True
        assert data["official_title"] == "Urban Planner"

    def test_grant_official_without_title(self, client, admin_auth_headers, test_user):
        """Test granting official status without title."""
        response = client.post(
            "/api/admin/officials/grant",
            headers=admin_auth_headers,
            json={"user_id": test_user.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_official"] is True
        assert data["official_title"] is None

    def test_grant_official_unauthorized(self, client, auth_headers, other_user):
        """Test that non-admins cannot grant official status."""
        response = client.post(
            "/api/admin/officials/grant",
            headers=auth_headers,
            json={"user_id": other_user.id},
        )

        assert response.status_code == 403

    def test_grant_already_official(self, client, admin_auth_headers, official_user):
        """Test that granting to already official user fails."""
        response = client.post(
            "/api/admin/officials/grant",
            headers=admin_auth_headers,
            json={"user_id": official_user.id},
        )

        assert response.status_code == 400

    def test_grant_nonexistent_user(self, client, admin_auth_headers):
        """Test that granting to nonexistent user fails."""
        response = client.post(
            "/api/admin/officials/grant",
            headers=admin_auth_headers,
            json={"user_id": 99999},
        )

        assert response.status_code == 404


class TestRevokeOfficialStatus:
    """Tests for POST /admin/officials/revoke."""

    def test_revoke_official_success(self, client, admin_auth_headers, official_user):
        """Test revoking official status."""
        response = client.post(
            "/api/admin/officials/revoke",
            headers=admin_auth_headers,
            json={"user_id": official_user.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_official"] is False
        assert data["official_title"] is None

    def test_revoke_unauthorized(self, client, auth_headers, official_user):
        """Test that non-admins cannot revoke official status."""
        response = client.post(
            "/api/admin/officials/revoke",
            headers=auth_headers,
            json={"user_id": official_user.id},
        )

        assert response.status_code == 403

    def test_revoke_not_official(self, client, admin_auth_headers, test_user):
        """Test that revoking from non-official fails."""
        response = client.post(
            "/api/admin/officials/revoke",
            headers=admin_auth_headers,
            json={"user_id": test_user.id},
        )

        assert response.status_code == 400


class TestUpdateOfficialTitle:
    """Tests for PUT /admin/officials/{user_id}/title."""

    def test_update_title_success(self, client, admin_auth_headers, official_user):
        """Test updating an official's title."""
        response = client.put(
            f"/api/admin/officials/{official_user.id}/title",
            headers=admin_auth_headers,
            params={"title": "Senior City Planner"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["official_title"] == "Senior City Planner"

    def test_update_title_unauthorized(self, client, auth_headers, official_user):
        """Test that non-admins cannot update titles."""
        response = client.put(
            f"/api/admin/officials/{official_user.id}/title",
            headers=auth_headers,
            params={"title": "New Title"},
        )

        assert response.status_code == 403

    def test_update_title_not_official(self, client, admin_auth_headers, test_user):
        """Test that updating non-official fails."""
        response = client.put(
            f"/api/admin/officials/{test_user.id}/title",
            headers=admin_auth_headers,
            params={"title": "New Title"},
        )

        assert response.status_code == 400


class TestListOfficialRequests:
    """Tests for GET /admin/officials/requests."""

    def test_list_requests_success(self, client, admin_auth_headers, requesting_user):
        """Test listing pending official requests."""
        response = client.get(
            "/api/admin/officials/requests",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == requesting_user.id
        assert data[0]["official_title_request"] == "Community Leader"

    def test_list_requests_unauthorized(self, client, auth_headers):
        """Test that non-admins cannot list requests."""
        response = client.get(
            "/api/admin/officials/requests",
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestRejectOfficialRequest:
    """Tests for POST /admin/officials/requests/{user_id}/reject."""

    def test_reject_request_success(
        self, client, admin_auth_headers, requesting_user, db_session
    ):
        """Test rejecting an official request."""
        response = client.post(
            f"/api/admin/officials/requests/{requesting_user.id}/reject",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Official request rejected"

        # Verify in database
        db_session.refresh(requesting_user)
        assert requesting_user.requests_official_status is False

    def test_reject_request_unauthorized(self, client, auth_headers, requesting_user):
        """Test that non-admins cannot reject requests."""
        response = client.post(
            f"/api/admin/officials/requests/{requesting_user.id}/reject",
            headers=auth_headers,
        )

        assert response.status_code == 403

    def test_reject_no_request(self, client, admin_auth_headers, test_user):
        """Test that rejecting user without request fails."""
        response = client.post(
            f"/api/admin/officials/requests/{test_user.id}/reject",
            headers=admin_auth_headers,
        )

        assert response.status_code == 400
