"""
Tests for admin security endpoints (Phase 2).

Tests the admin API for viewing and managing security events.
"""

import pytest
from fastapi import status

import repositories.db_models as db_models
from repositories.login_event_repository import LoginEventRepository


@pytest.fixture
def sample_events(db_session, admin_user, test_user) -> list[db_models.LoginEvent]:
    """Create sample login events for testing."""
    repo = LoginEventRepository(db_session)

    events = []

    # Successful logins
    events.append(
        repo.create_event(
            event_type=db_models.LoginEventType.LOGIN_SUCCESS,
            user_id=admin_user.id,
            email=admin_user.email,
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        )
    )
    events.append(
        repo.create_event(
            event_type=db_models.LoginEventType.LOGIN_SUCCESS,
            user_id=test_user.id,
            email=test_user.email,
            ip_address="10.0.0.50",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X) Firefox/121.0",
        )
    )

    # Failed logins
    events.append(
        repo.create_event(
            event_type=db_models.LoginEventType.LOGIN_FAILED,
            email="unknown@test.com",
            ip_address="192.168.1.200",
            user_agent="curl/7.68.0",
            failure_reason=db_models.LoginFailureReason.USER_NOT_FOUND,
        )
    )
    events.append(
        repo.create_event(
            event_type=db_models.LoginEventType.LOGIN_FAILED,
            user_id=test_user.id,
            email=test_user.email,
            ip_address="10.0.0.100",
            user_agent="Python/3.10 requests/2.28.0",
            failure_reason=db_models.LoginFailureReason.INVALID_PASSWORD,
        )
    )

    return events


class TestSecurityEventsEndpoint:
    """Tests for GET /api/admin/security/events endpoint."""

    def test_requires_admin_auth(self, client):
        """Endpoint requires authentication."""
        response = client.get("/api/admin/security/events")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_requires_admin_role(self, client, auth_headers):
        """Endpoint requires admin role."""
        response = client.get(
            "/api/admin/security/events",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_returns_events_list(self, client, admin_auth_headers, sample_events):
        """Returns paginated list of events."""
        response = client.get(
            "/api/admin/security/events",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "events" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert data["total"] >= 4  # At least our sample events

    def test_filter_by_event_type(self, client, admin_auth_headers, sample_events):
        """Can filter by event type."""
        response = client.get(
            "/api/admin/security/events?event_type=login_failed",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        for event in data["events"]:
            assert event["event_type"] == "login_failed"

    def test_filter_by_user_id(
        self, client, admin_auth_headers, sample_events, test_user
    ):
        """Can filter by user ID."""
        response = client.get(
            f"/api/admin/security/events?user_id={test_user.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        for event in data["events"]:
            assert event["user_id"] == test_user.id

    def test_pagination(self, client, admin_auth_headers, sample_events):
        """Pagination works correctly."""
        response = client.get(
            "/api/admin/security/events?limit=2&skip=0",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert len(data["events"]) <= 2
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_ip_masking(self, client, admin_auth_headers, sample_events):
        """IP addresses are masked for privacy."""
        response = client.get(
            "/api/admin/security/events",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        for event in data["events"]:
            if event["ip_address"]:
                # Should be masked like "192.x.x.x"
                assert "x.x.x" in event["ip_address"]


class TestSecuritySummaryEndpoint:
    """Tests for GET /api/admin/security/summary endpoint."""

    def test_requires_admin_auth(self, client):
        """Endpoint requires authentication."""
        response = client.get("/api/admin/security/summary")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_summary(self, client, admin_auth_headers, sample_events):
        """Returns security summary with counts."""
        response = client.get(
            "/api/admin/security/summary",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "total_events_24h" in data
        assert "successful_logins_24h" in data
        assert "failed_attempts_24h" in data
        assert "unique_ips_24h" in data
        assert "admin_logins_24h" in data
        assert "suspicious_ips" in data
        assert "recent_admin_logins" in data


class TestUserSecurityEventsEndpoint:
    """Tests for GET /api/admin/security/events/user/{user_id} endpoint."""

    def test_returns_user_events(
        self, client, admin_auth_headers, sample_events, test_user
    ):
        """Returns events for a specific user."""
        response = client.get(
            f"/api/admin/security/events/user/{test_user.id}",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        for event in data["events"]:
            assert event["user_id"] == test_user.id


class TestFailedAttemptsEndpoint:
    """Tests for GET /api/admin/security/failed-attempts endpoint."""

    def test_returns_only_failures(self, client, admin_auth_headers, sample_events):
        """Returns only failed login attempts."""
        response = client.get(
            "/api/admin/security/failed-attempts",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        for event in data["events"]:
            assert event["event_type"] == "login_failed"

    def test_time_window_filter(self, client, admin_auth_headers, sample_events):
        """Can specify time window."""
        response = client.get(
            "/api/admin/security/failed-attempts?hours=1",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK


class TestBruteForceRisksEndpoint:
    """Tests for GET /api/admin/security/brute-force-risks endpoint."""

    def test_returns_risks(self, client, admin_auth_headers):
        """Returns brute force risk assessment."""
        response = client.get(
            "/api/admin/security/brute-force-risks",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "risks" in data
        assert "count" in data


class TestSecurityCleanupEndpoint:
    """Tests for POST /api/admin/security/cleanup endpoint."""

    def test_requires_admin_auth(self, client):
        """Endpoint requires authentication."""
        response = client.post("/api/admin/security/cleanup")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cleanup_returns_results(self, client, admin_auth_headers):
        """Cleanup returns deletion count."""
        response = client.post(
            "/api/admin/security/cleanup?retention_days=90",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "deleted_count" in data
        assert "retention_days" in data
        assert "triggered_at" in data
        assert data["retention_days"] == 90

    def test_retention_days_validation(self, client, admin_auth_headers):
        """Retention days must be within valid range."""
        # Too low
        response = client.post(
            "/api/admin/security/cleanup?retention_days=10",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Too high
        response = client.post(
            "/api/admin/security/cleanup?retention_days=500",
            headers=admin_auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
