"""Tests for legal content endpoints."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestTermsOfService:
    """Tests for Terms of Service endpoint."""

    def test_get_terms_english(self, client: TestClient) -> None:
        """Test getting Terms of Service in English."""
        response = client.get("/api/legal/terms/en")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert "last_updated" in data
        assert "html_content" in data
        assert isinstance(data["html_content"], str)
        assert len(data["html_content"]) > 0

    def test_get_terms_french(self, client: TestClient) -> None:
        """Test getting Terms of Service in French."""
        response = client.get("/api/legal/terms/fr")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert "last_updated" in data
        assert "html_content" in data
        # French content should contain French text
        assert (
            "Acceptation" in data["html_content"]
            or "conditions" in data["html_content"]
        )

    def test_terms_contains_interpolated_values(self, client: TestClient) -> None:
        """Test that Terms of Service contains interpolated config values."""
        response = client.get("/api/legal/terms/en")
        data = response.json()

        # Should not contain uninterpolated placeholders
        assert "{{instanceName}}" not in data["html_content"]
        assert "{{entityName}}" not in data["html_content"]
        assert "{{contactEmail}}" not in data["html_content"]

    def test_terms_fallback_to_english(self, client: TestClient) -> None:
        """Test that unsupported locale falls back to English."""
        response = client.get("/api/legal/terms/de")

        assert response.status_code == 200
        data = response.json()

        # Should get English content as fallback
        assert "html_content" in data
        assert len(data["html_content"]) > 0


class TestPrivacyPolicy:
    """Tests for Privacy Policy endpoint."""

    def test_get_privacy_english(self, client: TestClient) -> None:
        """Test getting Privacy Policy in English."""
        response = client.get("/api/legal/privacy/en")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert "last_updated" in data
        assert "html_content" in data
        assert isinstance(data["html_content"], str)
        assert len(data["html_content"]) > 0

    def test_get_privacy_french(self, client: TestClient) -> None:
        """Test getting Privacy Policy in French."""
        response = client.get("/api/legal/privacy/fr")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert "html_content" in data
        # French content should contain French text
        assert (
            "Confidentialité" in data["html_content"]
            or "données" in data["html_content"]
        )

    def test_privacy_contains_interpolated_values(self, client: TestClient) -> None:
        """Test that Privacy Policy contains interpolated config values."""
        response = client.get("/api/legal/privacy/en")
        data = response.json()

        # Should not contain uninterpolated placeholders
        assert "{{instanceName}}" not in data["html_content"]
        assert "{{contactEmail}}" not in data["html_content"]
        assert "{{privacyAuthority}}" not in data["html_content"]

    def test_privacy_fallback_to_english(self, client: TestClient) -> None:
        """Test that unsupported locale falls back to English."""
        response = client.get("/api/legal/privacy/es")

        assert response.status_code == 200
        data = response.json()

        # Should get English content as fallback
        assert "html_content" in data
        assert len(data["html_content"]) > 0


class TestLegalContentFormat:
    """Tests for legal content formatting."""

    def test_content_is_html(self, client: TestClient) -> None:
        """Test that content is properly converted to HTML."""
        response = client.get("/api/legal/terms/en")
        data = response.json()

        # Should contain HTML tags from markdown conversion
        assert "<h2>" in data["html_content"] or "<p>" in data["html_content"]

    def test_content_has_sections(self, client: TestClient) -> None:
        """Test that content contains expected sections."""
        response = client.get("/api/legal/terms/en")
        data = response.json()

        # Terms should have key sections
        content = data["html_content"].lower()
        assert "acceptance" in content or "terms" in content

    def test_version_format(self, client: TestClient) -> None:
        """Test that version follows expected format."""
        response = client.get("/api/legal/terms/en")
        data = response.json()

        # Version should be a string like "1.0"
        assert isinstance(data["version"], str)
        assert data["version"]  # Not empty

    def test_last_updated_format(self, client: TestClient) -> None:
        """Test that last_updated is present."""
        response = client.get("/api/legal/terms/en")
        data = response.json()

        # last_updated should be a date string
        assert isinstance(data["last_updated"], str)
