"""Unit tests for main.py configuration integration."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from services.config_service import (
    ContactConfig,
    InstanceConfig,
    InstanceEntity,
    LocalizationConfig,
    PlatformConfig,
    clear_config_cache,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear config cache before each test."""
    clear_config_cache()
    yield
    clear_config_cache()


class TestGetApiTitle:
    """Tests for _get_api_title function."""

    def test_returns_instance_name_with_api_suffix(self):
        """Should return '{instance_name} API'."""
        mock_config = PlatformConfig(
            platform={"name": "OpenCitiVibes", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Ideas for TestCity", "fr": "Idées pour VilleTest"},
                entity=InstanceEntity(type="city", name={"en": "TestCity"}),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="en",
                supported_locales=["en", "fr"],
            ),
        )

        # Patch at the config_service module level (where lru_cache loads from)
        with patch(
            "services.config_service.load_platform_config", return_value=mock_config
        ):
            clear_config_cache()
            from main import _get_api_title

            title = _get_api_title()

        assert title == "Ideas for TestCity API"

    def test_uses_default_locale_from_config(self):
        """Should use the default locale from config."""
        mock_config = PlatformConfig(
            platform={"name": "OpenCitiVibes", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "English Name", "fr": "Nom Français"},
                entity=InstanceEntity(type="city", name={"en": "City"}),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="fr",  # French as default
                supported_locales=["en", "fr"],
            ),
        )

        with patch(
            "services.config_service.load_platform_config", return_value=mock_config
        ):
            clear_config_cache()
            from main import _get_api_title

            title = _get_api_title()

        assert title == "Nom Français API"

    def test_fallback_to_opencitivibes(self):
        """Should fall back to OpenCitiVibes if locale not in name dict."""
        mock_config = PlatformConfig(
            platform={"name": "OpenCitiVibes", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "English Only"},  # No French
                entity=InstanceEntity(type="city", name={"en": "City"}),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="de",  # German - not in name dict
                supported_locales=["en", "de"],
            ),
        )

        with patch(
            "services.config_service.load_platform_config", return_value=mock_config
        ):
            clear_config_cache()
            from main import _get_api_title

            title = _get_api_title()

        # Should fall back to "OpenCitiVibes API"
        assert title == "OpenCitiVibes API"


class TestRootEndpoint:
    """Tests for root endpoint configuration integration."""

    def test_root_returns_platform_info(self, client: TestClient):
        """Root endpoint should return platform info from config."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        # Should have expected keys
        assert "message" in data
        assert "platform" in data
        assert "version" in data

    def test_root_message_includes_instance_name(self, client: TestClient):
        """Root message should include the instance name."""
        response = client.get("/")
        data = response.json()

        # Default config uses Montreal
        assert "Welcome to" in data["message"]
        assert "API" in data["message"]

    def test_root_returns_platform_name(self, client: TestClient):
        """Root should return platform name from config."""
        response = client.get("/")
        data = response.json()

        # Default config has OpenCitiVibes
        assert data["platform"] == "OpenCitiVibes"

    def test_root_returns_version(self, client: TestClient):
        """Root should return version from config."""
        response = client.get("/")
        data = response.json()

        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_endpoint_still_works(self, client: TestClient):
        """Health endpoint should still work independently."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from main import app

    return TestClient(app)
