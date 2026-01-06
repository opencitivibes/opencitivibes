"""Tests for share_router endpoints."""

from fastapi import status


class TestShareRouter:
    """Test suite for share API endpoints."""

    def test_record_share_success(self, client, test_idea):
        """Should record a share event (no auth required)."""
        response = client.post(
            f"/api/shares/{test_idea.id}",
            json={"platform": "twitter", "referrer_url": "https://example.com"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["idea_id"] == test_idea.id
        assert data["platform"] == "twitter"
        assert "id" in data
        assert "created_at" in data

    def test_record_share_without_referrer(self, client, test_idea):
        """Should record a share without referrer URL."""
        response = client.post(
            f"/api/shares/{test_idea.id}",
            json={"platform": "facebook"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["platform"] == "facebook"

    def test_record_share_all_platforms(self, client, test_idea):
        """Should support all platforms."""
        platforms = ["twitter", "facebook", "linkedin", "whatsapp", "copy_link"]

        for platform in platforms:
            response = client.post(
                f"/api/shares/{test_idea.id}",
                json={"platform": platform},
            )
            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["platform"] == platform

    def test_record_share_invalid_platform(self, client, test_idea):
        """Should reject invalid platform."""
        response = client.post(
            f"/api/shares/{test_idea.id}",
            json={"platform": "invalid_platform"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_record_share_idea_not_found(self, client):
        """Should return 404 for non-existent idea."""
        response = client.post(
            "/api/shares/99999",
            json={"platform": "twitter"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_share_analytics_success(self, client, test_idea):
        """Should return share analytics for an idea."""
        # Create some shares first
        client.post(f"/api/shares/{test_idea.id}", json={"platform": "twitter"})
        client.post(f"/api/shares/{test_idea.id}", json={"platform": "twitter"})
        client.post(f"/api/shares/{test_idea.id}", json={"platform": "facebook"})

        response = client.get(f"/api/shares/{test_idea.id}/analytics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["idea_id"] == test_idea.id
        assert data["total_shares"] == 3
        assert data["by_platform"]["twitter"] == 2
        assert data["by_platform"]["facebook"] == 1
        assert "last_7_days" in data

    def test_get_share_analytics_no_shares(self, client, test_idea):
        """Should return zero counts for idea with no shares."""
        response = client.get(f"/api/shares/{test_idea.id}/analytics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_shares"] == 0
        assert data["by_platform"] == {}

    def test_get_share_analytics_idea_not_found(self, client):
        """Should return 404 for non-existent idea."""
        response = client.get("/api/shares/99999/analytics")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAdminShareRouter:
    """Test suite for admin share analytics endpoints."""

    def test_get_admin_analytics_requires_auth(self, client):
        """Should require authentication."""
        response = client.get("/api/admin/analytics/shares")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_admin_analytics_requires_admin(self, client, auth_headers):
        """Should require admin privileges."""
        response = client.get(
            "/api/admin/analytics/shares",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_admin_analytics_success(self, client, admin_auth_headers, test_idea):
        """Should return admin analytics for admins."""
        # Create some shares
        client.post(f"/api/shares/{test_idea.id}", json={"platform": "twitter"})
        client.post(f"/api/shares/{test_idea.id}", json={"platform": "facebook"})

        response = client.get(
            "/api/admin/analytics/shares",
            headers=admin_auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_shares"] == 2
        assert "platform_distribution" in data
        assert "top_shared_ideas" in data
        assert "shares_last_7_days" in data
        assert "shares_last_30_days" in data
        assert "generated_at" in data

    def test_get_admin_analytics_empty(self, client, admin_auth_headers):
        """Should return empty analytics when no shares."""
        response = client.get(
            "/api/admin/analytics/shares",
            headers=admin_auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_shares"] == 0
        assert data["platform_distribution"] == {}
        assert data["top_shared_ideas"] == []
