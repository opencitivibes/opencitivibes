"""Tests for admin user filtering functionality."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from repositories import db_models


class TestAdminUserFilters:
    """Tests for GET /admin/users with filters."""

    def test_filter_by_role_global_admin(
        self, client: TestClient, admin_auth_headers: dict, db_session: Session
    ):
        """Test filtering users by global admin role."""
        response = client.get(
            "/api/admin/users?role=global_admin",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for user in data["users"]:
            assert user["is_global_admin"] is True

    def test_filter_by_role_regular(
        self, client: TestClient, admin_auth_headers: dict, db_session: Session
    ):
        """Test filtering users by regular role (no admin/official status)."""
        response = client.get(
            "/api/admin/users?role=regular",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for user in data["users"]:
            assert user["is_global_admin"] is False
            assert user["is_official"] is False
            assert user["has_category_admin_role"] is False

    def test_filter_by_official_status(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        db_session: Session,
        official_user: db_models.User,
    ):
        """Test filtering users by official status."""
        response = client.get(
            "/api/admin/users?is_official=true",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for user in data["users"]:
            assert user["is_official"] is True
        # Verify official_user is in results
        user_ids = [u["id"] for u in data["users"]]
        assert official_user.id in user_ids

    def test_filter_by_trust_score_range(
        self, client: TestClient, admin_auth_headers: dict, db_session: Session
    ):
        """Test filtering users by trust score range."""
        # Create user with low trust score
        low_trust_user = db_models.User(
            email="lowtrust@test.com",
            username="lowtrust_user",
            display_name="Low Trust User",
            hashed_password="hashedpass",
            trust_score=20,
        )
        db_session.add(low_trust_user)
        db_session.commit()
        db_session.refresh(low_trust_user)

        # Filter for low trust users (0-40)
        response = client.get(
            "/api/admin/users?trust_score_min=0&trust_score_max=40",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for user in data["users"]:
            assert 0 <= user["trust_score"] <= 40
        # Verify our low trust user is in results
        user_ids = [u["id"] for u in data["users"]]
        assert low_trust_user.id in user_ids

    def test_filter_by_active_status(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        db_session: Session,
        test_user: db_models.User,
    ):
        """Test filtering active/inactive users."""
        # Create inactive user
        inactive_user = db_models.User(
            email="inactive@test.com",
            username="inactive_user",
            display_name="Inactive User",
            hashed_password="hashedpass",
            is_active=False,
        )
        db_session.add(inactive_user)
        db_session.commit()
        db_session.refresh(inactive_user)

        # Filter excluding inactive
        response = client.get(
            "/api/admin/users?include_inactive=false",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for user in data["users"]:
            assert user["is_active"] is True
        # Verify inactive user is NOT in results
        user_ids = [u["id"] for u in data["users"]]
        assert inactive_user.id not in user_ids

    def test_filter_pagination(
        self, client: TestClient, admin_auth_headers: dict, db_session: Session
    ):
        """Test that filters work correctly with pagination."""
        response = client.get(
            "/api/admin/users?page=1&page_size=5",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["users"]) <= 5
        assert "total" in data
        assert "page" in data
        assert "total_pages" in data

    def test_combined_filters(
        self, client: TestClient, admin_auth_headers: dict, db_session: Session
    ):
        """Test multiple filters applied simultaneously."""
        response = client.get(
            "/api/admin/users?role=regular&trust_score_min=40&trust_score_max=60&include_inactive=false",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        for user in data["users"]:
            assert user["is_global_admin"] is False
            assert user["is_active"] is True
            assert 40 <= user["trust_score"] <= 60

    def test_invalid_role_filter(
        self, client: TestClient, admin_auth_headers: dict, db_session: Session
    ):
        """Test that invalid role values are rejected."""
        response = client.get(
            "/api/admin/users?role=invalid_role",
            headers=admin_auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_response_includes_new_fields(
        self, client: TestClient, admin_auth_headers: dict, db_session: Session
    ):
        """Test that response includes is_official, official_title, has_category_admin_role."""
        response = client.get(
            "/api/admin/users?page=1&page_size=5",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        if data["users"]:
            user = data["users"][0]
            assert "is_official" in user
            assert "official_title" in user
            assert "has_category_admin_role" in user

    def test_filter_requires_admin(
        self, client: TestClient, auth_headers: dict, db_session: Session
    ):
        """Test that filter endpoint requires admin privileges."""
        response = client.get(
            "/api/admin/users?role=regular",
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_filter_by_role_official(
        self,
        client: TestClient,
        admin_auth_headers: dict,
        db_session: Session,
        official_user: db_models.User,
    ):
        """Test filtering by official role."""
        response = client.get(
            "/api/admin/users?role=official",
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for user in data["users"]:
            assert user["is_official"] is True
