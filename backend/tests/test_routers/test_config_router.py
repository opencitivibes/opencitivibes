"""Integration tests for config router."""

from fastapi.testclient import TestClient


class TestConfigRouter:
    """Test config API endpoints."""

    def test_get_public_config(self, client: TestClient):
        """Test getting public platform configuration."""
        response = client.get("/api/config/public")
        assert response.status_code == 200

        data = response.json()

        # Check required top-level keys
        assert "platform" in data
        assert "instance" in data
        assert "localization" in data
        assert "features" in data
        assert "contact" in data

    def test_public_config_structure(self, client: TestClient):
        """Test structure of public config response."""
        response = client.get("/api/config/public")
        assert response.status_code == 200

        data = response.json()

        # Platform info
        assert "name" in data["platform"]

        # Instance info
        assert "name" in data["instance"]
        assert "entity" in data["instance"]
        assert "type" in data["instance"]["entity"]
        assert "name" in data["instance"]["entity"]

        # Localization
        assert "default_locale" in data["localization"]
        assert "supported_locales" in data["localization"]

        # Contact - should only have email (no support_email for privacy)
        assert "email" in data["contact"]

    def test_public_config_does_not_expose_sensitive_data(self, client: TestClient):
        """Test that sensitive data is not exposed."""
        response = client.get("/api/config/public")
        assert response.status_code == 200

        data = response.json()

        # Support email should not be in public config
        if "contact" in data:
            assert "support_email" not in data["contact"]

        # Legal details should be limited
        if "legal" in data and data["legal"] is not None:
            # Only jurisdiction should be exposed
            assert "jurisdiction" in data["legal"]
            # Courts and other details should not be directly exposed at top level
            # (jurisdiction contains the courts info localized)

    def test_public_config_contains_branding(self, client: TestClient):
        """Test that branding info is included."""
        response = client.get("/api/config/public")
        assert response.status_code == 200

        data = response.json()

        # Branding may be present
        if "branding" in data and data["branding"] is not None:
            assert "primary_color" in data["branding"]
            assert "secondary_color" in data["branding"]

    def test_public_config_contains_features(self, client: TestClient):
        """Test that feature flags are included."""
        response = client.get("/api/config/public")
        assert response.status_code == 200

        data = response.json()

        # Features should be a dict (possibly empty)
        assert isinstance(data["features"], dict)
