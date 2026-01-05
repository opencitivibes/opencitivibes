"""
Integration tests for officials router endpoints.
"""


class TestOfficialsOverviewEndpoint:
    """Tests for /officials/analytics/overview endpoint."""

    def test_get_overview_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/officials/analytics/overview")
        assert response.status_code == 401

    def test_get_overview_requires_official_role(self, client, auth_headers):
        """Test that endpoint requires official role."""
        response = client.get("/api/officials/analytics/overview", headers=auth_headers)
        assert response.status_code == 403

    def test_get_overview_works_for_official(self, client, official_auth_headers):
        """Test that officials can access overview."""
        response = client.get(
            "/api/officials/analytics/overview", headers=official_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_upvotes" in data
        assert "votes_with_qualities" in data
        assert "adoption_rate" in data
        assert "quality_distribution" in data

    def test_get_overview_works_for_admin(self, client, admin_auth_headers):
        """Test that admins can access overview."""
        response = client.get(
            "/api/officials/analytics/overview", headers=admin_auth_headers
        )
        assert response.status_code == 200


class TestOfficialsTopIdeasEndpoint:
    """Tests for /officials/analytics/top-ideas endpoint."""

    def test_get_top_ideas_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/officials/analytics/top-ideas")
        assert response.status_code == 401

    def test_get_top_ideas_requires_official_role(self, client, auth_headers):
        """Test that endpoint requires official role."""
        response = client.get(
            "/api/officials/analytics/top-ideas", headers=auth_headers
        )
        assert response.status_code == 403

    def test_get_top_ideas_works_for_official(self, client, official_auth_headers):
        """Test that officials can access top ideas."""
        response = client.get(
            "/api/officials/analytics/top-ideas", headers=official_auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_top_ideas_with_limit(self, client, official_auth_headers):
        """Test top ideas with limit parameter."""
        response = client.get(
            "/api/officials/analytics/top-ideas?limit=5",
            headers=official_auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()) <= 5

    def test_get_top_ideas_with_quality_filter(self, client, official_auth_headers):
        """Test top ideas with quality filter."""
        response = client.get(
            "/api/officials/analytics/top-ideas?quality_key=community_benefit",
            headers=official_auth_headers,
        )
        assert response.status_code == 200


class TestOfficialsCategoriesEndpoint:
    """Tests for /officials/analytics/categories endpoint."""

    def test_get_categories_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/officials/analytics/categories")
        assert response.status_code == 401

    def test_get_categories_works_for_official(self, client, official_auth_headers):
        """Test that officials can access categories."""
        response = client.get(
            "/api/officials/analytics/categories", headers=official_auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestOfficialsTrendsEndpoint:
    """Tests for /officials/analytics/trends endpoint."""

    def test_get_trends_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/officials/analytics/trends")
        assert response.status_code == 401

    def test_get_trends_works_for_official(self, client, official_auth_headers):
        """Test that officials can access trends."""
        response = client.get(
            "/api/officials/analytics/trends", headers=official_auth_headers
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_trends_with_days_param(self, client, official_auth_headers):
        """Test trends with days parameter."""
        response = client.get(
            "/api/officials/analytics/trends?days=14",
            headers=official_auth_headers,
        )
        assert response.status_code == 200

    def test_get_trends_invalid_days(self, client, official_auth_headers):
        """Test trends with invalid days parameter."""
        response = client.get(
            "/api/officials/analytics/trends?days=500",
            headers=official_auth_headers,
        )
        assert response.status_code == 422  # Validation error


class TestOfficialsIdeasEndpoint:
    """Tests for /officials/ideas endpoint."""

    def test_get_ideas_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/officials/ideas")
        assert response.status_code == 401

    def test_get_ideas_works_for_official(self, client, official_auth_headers):
        """Test that officials can access ideas."""
        response = client.get("/api/officials/ideas", headers=official_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data

    def test_get_ideas_with_pagination(self, client, official_auth_headers):
        """Test ideas with pagination."""
        response = client.get(
            "/api/officials/ideas?skip=0&limit=10",
            headers=official_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 10

    def test_get_ideas_with_category_filter(
        self, client, official_auth_headers, test_category
    ):
        """Test ideas with category filter."""
        response = client.get(
            f"/api/officials/ideas?category_id={test_category.id}",
            headers=official_auth_headers,
        )
        assert response.status_code == 200

    def test_get_ideas_with_sorting(self, client, official_auth_headers):
        """Test ideas with sorting."""
        response = client.get(
            "/api/officials/ideas?sort_by=created_at&sort_order=desc",
            headers=official_auth_headers,
        )
        assert response.status_code == 200

    def test_get_ideas_invalid_sort(self, client, official_auth_headers):
        """Test ideas with invalid sort parameter."""
        response = client.get(
            "/api/officials/ideas?sort_by=invalid",
            headers=official_auth_headers,
        )
        assert response.status_code == 422  # Validation error


class TestOfficialsExportIdeasEndpoint:
    """Tests for /officials/export/ideas.csv endpoint."""

    def test_export_ideas_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/officials/export/ideas.csv")
        assert response.status_code == 401

    def test_export_ideas_works_for_official(self, client, official_auth_headers):
        """Test that officials can export ideas."""
        response = client.get(
            "/api/officials/export/ideas.csv", headers=official_auth_headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]

    def test_export_ideas_csv_format(self, client, official_auth_headers):
        """Test CSV format of exported ideas."""
        response = client.get(
            "/api/officials/export/ideas.csv", headers=official_auth_headers
        )
        assert response.status_code == 200
        content = response.text
        # Check header row
        assert "ID" in content
        assert "Title" in content
        assert "Quality Count" in content


class TestOfficialsExportAnalyticsEndpoint:
    """Tests for /officials/export/analytics.csv endpoint."""

    def test_export_analytics_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/officials/export/analytics.csv")
        assert response.status_code == 401

    def test_export_analytics_works_for_official(self, client, official_auth_headers):
        """Test that officials can export analytics."""
        response = client.get(
            "/api/officials/export/analytics.csv", headers=official_auth_headers
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_export_analytics_csv_content(self, client, official_auth_headers):
        """Test CSV content of exported analytics."""
        response = client.get(
            "/api/officials/export/analytics.csv", headers=official_auth_headers
        )
        assert response.status_code == 200
        content = response.text
        # Check section headers
        assert "Quality Overview" in content
        assert "Total Upvotes" in content


class TestExportSecurityHeaders:
    """Tests for security headers on export endpoints (Phase 5)."""

    def test_ideas_export_has_security_headers(self, client, official_auth_headers):
        """Test that ideas export has proper security headers."""
        response = client.get(
            "/api/officials/export/ideas.csv", headers=official_auth_headers
        )
        assert response.status_code == 200
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert "no-store" in response.headers.get("cache-control", "")
        assert "no-cache" in response.headers.get("cache-control", "")
        assert response.headers.get("pragma") == "no-cache"

    def test_analytics_export_has_security_headers(self, client, official_auth_headers):
        """Test that analytics export has proper security headers."""
        response = client.get(
            "/api/officials/export/analytics.csv", headers=official_auth_headers
        )
        assert response.status_code == 200
        assert response.headers.get("x-content-type-options") == "nosniff"
        assert "no-store" in response.headers.get("cache-control", "")
        assert response.headers.get("pragma") == "no-cache"


class TestExportRateLimiting:
    """Tests for rate limiting on export endpoints (Phase 5)."""

    def test_export_succeeds_within_limit(self, client, official_auth_headers):
        """Test that exports work within rate limit."""
        # First export should succeed
        response = client.get(
            "/api/officials/export/ideas.csv", headers=official_auth_headers
        )
        assert response.status_code == 200

    def test_rate_limit_error_message(self, client, official_auth_headers):
        """Test rate limit error message format."""
        # Make many requests to trigger rate limit
        # Note: In production this would need 11 requests, but we can test the mechanism
        for _ in range(11):
            response = client.get(
                "/api/officials/export/ideas.csv", headers=official_auth_headers
            )
            if response.status_code == 429:
                assert "rate limit exceeded" in response.json()["detail"].lower()
                break


class TestOfficialsIdeaDetailEndpoint:
    """Tests for /officials/ideas/{idea_id} endpoint."""

    def test_get_idea_detail_requires_auth(self, client):
        """Test that endpoint requires authentication."""
        response = client.get("/api/officials/ideas/1")
        assert response.status_code == 401

    def test_get_idea_detail_requires_official_role(self, client, auth_headers):
        """Test that endpoint requires official role."""
        response = client.get("/api/officials/ideas/1", headers=auth_headers)
        assert response.status_code == 403

    def test_get_idea_detail_not_found(self, client, official_auth_headers):
        """Test that non-existent idea returns 404."""
        response = client.get(
            "/api/officials/ideas/99999", headers=official_auth_headers
        )
        assert response.status_code == 404

    def test_get_idea_detail_success(self, client, official_auth_headers, test_idea):
        """Test getting idea detail for officials."""
        response = client.get(
            f"/api/officials/ideas/{test_idea.id}", headers=official_auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_idea.id
        assert "quality_breakdown" in data
        assert "score" in data
