"""Integration tests for analytics API endpoints."""

from datetime import date, timedelta

import pytest

from services.analytics_service import AnalyticsService


@pytest.fixture(autouse=True)
def clear_analytics_cache():
    """Clear analytics cache before each test."""
    AnalyticsService.invalidate_cache()
    yield
    AnalyticsService.invalidate_cache()


class TestAnalyticsRouterOverview:
    """Test cases for /api/admin/analytics/overview endpoint."""

    def test_overview_requires_auth(self, client):
        """Overview endpoint requires authentication."""
        response = client.get("/api/admin/analytics/overview")
        assert response.status_code == 401

    def test_overview_requires_admin(self, client, auth_headers):
        """Overview endpoint requires admin privileges."""
        response = client.get("/api/admin/analytics/overview", headers=auth_headers)
        assert response.status_code == 403

    def test_overview_returns_metrics(self, client, admin_auth_headers):
        """Overview endpoint returns expected data structure."""
        response = client.get(
            "/api/admin/analytics/overview", headers=admin_auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "total_users" in data
        assert "active_users" in data
        assert "total_ideas" in data
        assert "approved_ideas" in data
        assert "pending_ideas" in data
        assert "rejected_ideas" in data
        assert "total_votes" in data
        assert "total_comments" in data
        assert "ideas_this_week" in data
        assert "votes_this_week" in data
        assert "comments_this_week" in data
        assert "users_this_week" in data
        assert "generated_at" in data

    def test_overview_counts_users(
        self, client, admin_auth_headers, test_user, admin_user
    ):
        """Overview includes correct user counts."""
        response = client.get(
            "/api/admin/analytics/overview", headers=admin_auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        # At least the admin_user and test_user exist
        assert data["total_users"] >= 2
        assert data["active_users"] >= 2

    def test_overview_counts_ideas(
        self, client, admin_auth_headers, test_idea, pending_idea
    ):
        """Overview includes correct idea counts."""
        response = client.get(
            "/api/admin/analytics/overview", headers=admin_auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["total_ideas"] >= 2
        assert data["approved_ideas"] >= 1
        assert data["pending_ideas"] >= 1


class TestAnalyticsRouterTrends:
    """Test cases for /api/admin/analytics/trends endpoint."""

    def test_trends_requires_admin(self, client, auth_headers):
        """Trends endpoint requires admin privileges."""
        today = date.today()
        start = today - timedelta(days=30)
        response = client.get(
            "/api/admin/analytics/trends",
            params={"start_date": start.isoformat(), "end_date": today.isoformat()},
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_trends_requires_dates(self, client, admin_auth_headers):
        """Trends endpoint requires date parameters."""
        response = client.get("/api/admin/analytics/trends", headers=admin_auth_headers)
        assert response.status_code == 422

    def test_trends_returns_data(self, client, admin_auth_headers):
        """Trends endpoint returns expected data structure."""
        today = date.today()
        start = today - timedelta(days=30)

        response = client.get(
            "/api/admin/analytics/trends",
            params={
                "start_date": start.isoformat(),
                "end_date": today.isoformat(),
                "granularity": "week",
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "granularity" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "data" in data
        assert isinstance(data["data"], list)
        assert data["granularity"] == "week"

    @pytest.mark.parametrize("granularity", ["day", "week", "month"])
    def test_trends_granularity_options(self, client, admin_auth_headers, granularity):
        """Trends endpoint accepts all granularity options."""
        today = date.today()
        start = today - timedelta(days=30)

        response = client.get(
            "/api/admin/analytics/trends",
            params={
                "start_date": start.isoformat(),
                "end_date": today.isoformat(),
                "granularity": granularity,
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["granularity"] == granularity

    def test_trends_invalid_date_range(self, client, admin_auth_headers):
        """Trends endpoint rejects invalid date range."""
        today = date.today()
        response = client.get(
            "/api/admin/analytics/trends",
            params={
                "start_date": today.isoformat(),
                "end_date": (today - timedelta(days=1)).isoformat(),
                "granularity": "day",
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 422

    def test_trends_date_range_too_large(self, client, admin_auth_headers):
        """Trends endpoint rejects date range exceeding 2 years."""
        today = date.today()
        start = today - timedelta(days=365 * 3)  # 3 years
        response = client.get(
            "/api/admin/analytics/trends",
            params={
                "start_date": start.isoformat(),
                "end_date": today.isoformat(),
                "granularity": "month",
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 422


class TestAnalyticsRouterCategories:
    """Test cases for /api/admin/analytics/categories endpoint."""

    def test_categories_requires_admin(self, client, auth_headers):
        """Categories endpoint requires admin privileges."""
        response = client.get("/api/admin/analytics/categories", headers=auth_headers)
        assert response.status_code == 403

    def test_categories_returns_list(self, client, admin_auth_headers, test_category):
        """Categories endpoint returns list of category analytics."""
        response = client.get(
            "/api/admin/analytics/categories", headers=admin_auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "categories" in data
        assert "generated_at" in data
        assert isinstance(data["categories"], list)

    def test_categories_includes_metrics(
        self, client, admin_auth_headers, test_category, test_idea
    ):
        """Categories analytics includes expected metrics."""
        response = client.get(
            "/api/admin/analytics/categories", headers=admin_auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["categories"]) >= 1

        category = data["categories"][0]
        assert "id" in category
        assert "name_en" in category
        assert "name_fr" in category
        assert "total_ideas" in category
        assert "approved_ideas" in category
        assert "pending_ideas" in category
        assert "rejected_ideas" in category
        assert "total_votes" in category
        assert "total_comments" in category
        assert "avg_score" in category
        assert "approval_rate" in category


class TestAnalyticsRouterTopContributors:
    """Test cases for /api/admin/analytics/top-contributors endpoint."""

    def test_top_contributors_requires_admin(self, client, auth_headers):
        """Top contributors endpoint requires admin privileges."""
        response = client.get(
            "/api/admin/analytics/top-contributors", headers=auth_headers
        )
        assert response.status_code == 403

    def test_top_contributors_default(self, client, admin_auth_headers, test_user):
        """Top contributors returns data with default parameters."""
        response = client.get(
            "/api/admin/analytics/top-contributors", headers=admin_auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "type" in data
        assert "contributors" in data
        assert "generated_at" in data
        assert data["type"] == "ideas"  # Default type
        assert isinstance(data["contributors"], list)

    @pytest.mark.parametrize("contrib_type", ["ideas", "votes", "comments", "score"])
    def test_top_contributors_by_type(self, client, admin_auth_headers, contrib_type):
        """Top contributors accepts all type options."""
        response = client.get(
            "/api/admin/analytics/top-contributors",
            params={"type": contrib_type},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["type"] == contrib_type

    def test_top_contributors_limit_too_low(self, client, admin_auth_headers):
        """Top contributors rejects limit below 5."""
        response = client.get(
            "/api/admin/analytics/top-contributors",
            params={"limit": 2},
            headers=admin_auth_headers,
        )
        assert response.status_code == 422

    def test_top_contributors_limit_too_high(self, client, admin_auth_headers):
        """Top contributors rejects limit above 50."""
        response = client.get(
            "/api/admin/analytics/top-contributors",
            params={"limit": 100},
            headers=admin_auth_headers,
        )
        assert response.status_code == 422

    def test_top_contributors_valid_limit(self, client, admin_auth_headers):
        """Top contributors accepts valid limit range."""
        for limit_val in [5, 10, 25, 50]:
            response = client.get(
                "/api/admin/analytics/top-contributors",
                params={"limit": limit_val},
                headers=admin_auth_headers,
            )
            assert response.status_code == 200


class TestAnalyticsRouterCacheRefresh:
    """Test cases for /api/admin/analytics/refresh endpoint."""

    def test_refresh_requires_admin(self, client, auth_headers):
        """Refresh endpoint requires admin privileges."""
        response = client.post("/api/admin/analytics/refresh", headers=auth_headers)
        assert response.status_code == 403

    def test_refresh_all_cache(self, client, admin_auth_headers):
        """Refresh endpoint clears all cache."""
        response = client.post(
            "/api/admin/analytics/refresh", headers=admin_auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Cache invalidated successfully"
        assert data["key"] == "all"

    def test_refresh_specific_cache(self, client, admin_auth_headers):
        """Refresh endpoint can clear specific cache key."""
        response = client.post(
            "/api/admin/analytics/refresh",
            params={"cache_key": "overview"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Cache invalidated successfully"
        assert data["key"] == "overview"


class TestAnalyticsRouterExport:
    """Test cases for /api/admin/analytics/export endpoint."""

    def test_export_requires_admin(self, client, auth_headers):
        """Export endpoint requires admin privileges."""
        response = client.get("/api/admin/analytics/export", headers=auth_headers)
        assert response.status_code == 403

    def test_export_overview_csv(self, client, admin_auth_headers):
        """Export overview returns valid CSV."""
        response = client.get(
            "/api/admin/analytics/export",
            params={"data_type": "overview"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert "attachment" in response.headers["content-disposition"]

        content = response.text
        assert "Metric" in content
        assert "Total Users" in content
        assert "Total Ideas" in content

    def test_export_ideas_csv(self, client, admin_auth_headers, test_idea):
        """Export ideas returns valid CSV."""
        response = client.get(
            "/api/admin/analytics/export",
            params={"data_type": "ideas"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert "ID" in response.text
        assert "Title" in response.text
        assert "Category" in response.text

    def test_export_users_csv(self, client, admin_auth_headers, test_user):
        """Export users returns valid CSV."""
        response = client.get(
            "/api/admin/analytics/export",
            params={"data_type": "users"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert "Username" in response.text
        assert "Email" in response.text

    def test_export_categories_csv(self, client, admin_auth_headers, test_category):
        """Export categories returns valid CSV."""
        response = client.get(
            "/api/admin/analytics/export",
            params={"data_type": "categories"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        assert "Name (EN)" in response.text
        assert "Approval Rate" in response.text

    def test_export_with_date_filter(self, client, admin_auth_headers, test_idea):
        """Export with date filtering works."""
        today = date.today()
        start = today - timedelta(days=30)

        response = client.get(
            "/api/admin/analytics/export",
            params={
                "data_type": "ideas",
                "start_date": start.isoformat(),
                "end_date": today.isoformat(),
            },
            headers=admin_auth_headers,
        )
        assert response.status_code == 200

    def test_export_invalid_data_type(self, client, admin_auth_headers):
        """Export rejects invalid data type."""
        response = client.get(
            "/api/admin/analytics/export",
            params={"data_type": "invalid"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("data_type", ["overview", "ideas", "users", "categories"])
    def test_export_all_data_types(self, client, admin_auth_headers, data_type):
        """Export accepts all valid data types."""
        response = client.get(
            "/api/admin/analytics/export",
            params={"data_type": data_type},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
