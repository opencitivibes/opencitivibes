"""Unit tests for config service."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from services.config_service import (
    BrandingConfig,
    ContactConfig,
    InstanceConfig,
    InstanceEntity,
    LegalConfig,
    LocalizationConfig,
    PlatformConfig,
    clear_config_cache,
    get_config,
    get_entity_name,
    get_instance_name,
    load_platform_config,
)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear config cache before each test."""
    clear_config_cache()
    yield
    clear_config_cache()


class TestPlatformConfigModels:
    """Test Pydantic config models."""

    def test_instance_entity_creation(self):
        """Test InstanceEntity model creation."""
        entity = InstanceEntity(
            type="city",
            name={"en": "Montreal", "fr": "Montréal"},
            region={"en": "Quebec", "fr": "Québec"},
            country={"en": "Canada", "fr": "Canada"},
        )
        assert entity.type == "city"
        assert entity.name["en"] == "Montreal"
        assert entity.name["fr"] == "Montréal"

    def test_instance_entity_optional_fields(self):
        """Test InstanceEntity with optional fields."""
        entity = InstanceEntity(
            type="organization",
            name={"en": "Test Org"},
        )
        assert entity.type == "organization"
        assert entity.region is None
        assert entity.country is None

    def test_instance_config_creation(self):
        """Test InstanceConfig model creation."""
        config = InstanceConfig(
            name={"en": "Test Platform", "fr": "Plateforme Test"},
            entity=InstanceEntity(type="city", name={"en": "Test City"}),
            location={"display": {"en": "Test City"}, "timezone": "UTC"},
        )
        assert config.name["en"] == "Test Platform"
        assert config.entity.type == "city"
        assert config.location is not None
        assert config.location["timezone"] == "UTC"

    def test_contact_config_creation(self):
        """Test ContactConfig model creation."""
        config = ContactConfig(
            email="test@example.com",
            support_email="support@example.com",
        )
        assert config.email == "test@example.com"
        assert config.support_email == "support@example.com"

    def test_branding_config_defaults(self):
        """Test BrandingConfig default values."""
        config = BrandingConfig()
        assert config.primary_color == "#0066CC"
        assert config.secondary_color == "#003366"
        assert config.hero_image is None

    def test_branding_config_extended_fields(self):
        """Test BrandingConfig extended theming fields."""
        config = BrandingConfig(
            primary_color="#FF5500",
            secondary_color="#003366",
            primary_dark="#CC4400",
            accent="#14b8a6",
            success="#22c55e",
            warning="#eab308",
            error="#ef4444",
            dark_mode={"primary": "#4a9eff", "background": "#0f172a"},
            fonts={"heading": "Poppins", "body": "Inter"},
            font_url="https://fonts.googleapis.com/css2?family=Poppins",
            border_radius="lg",
            logo_dark="/images/logo-dark.svg",
            favicon="/favicon.ico",
            og_image="/og-image.png",
        )
        assert config.primary_dark == "#CC4400"
        assert config.accent == "#14b8a6"
        assert config.dark_mode is not None
        assert config.dark_mode["primary"] == "#4a9eff"
        assert config.fonts is not None
        assert config.fonts["heading"] == "Poppins"
        assert config.border_radius == "lg"
        assert config.logo_dark == "/images/logo-dark.svg"

    def test_branding_config_hex_color_validation(self):
        """Test BrandingConfig rejects invalid hex colors."""
        with pytest.raises(ValueError, match="Invalid hex color format"):
            BrandingConfig(primary_color="red")

        with pytest.raises(ValueError, match="Invalid hex color format"):
            BrandingConfig(primary_color="#FFF")  # 3 chars not allowed

        with pytest.raises(ValueError, match="Invalid hex color format"):
            BrandingConfig(accent="rgb(255,0,0)")

    def test_branding_config_dark_mode_validation(self):
        """Test BrandingConfig validates colors in dark_mode dict."""
        with pytest.raises(ValueError, match="Invalid hex color in dark_mode"):
            BrandingConfig(dark_mode={"primary": "invalid"})

    def test_branding_config_border_radius_values(self):
        """Test BrandingConfig accepts valid border_radius values."""
        for radius in ["none", "sm", "md", "lg", "full"]:
            config = BrandingConfig(border_radius=radius)
            assert config.border_radius == radius

    def test_branding_config_border_radius_invalid(self):
        """Test BrandingConfig rejects invalid border_radius."""
        with pytest.raises(ValueError):
            BrandingConfig(border_radius="extra-large")

    def test_localization_config_defaults(self):
        """Test LocalizationConfig default values."""
        config = LocalizationConfig()
        assert config.default_locale == "en"
        assert config.supported_locales == ["en"]


class TestLoadPlatformConfig:
    """Test config loading functionality."""

    def test_load_from_file(self):
        """Test loading config from a file."""
        config_data = {
            "platform": {"name": "TestPlatform", "version": "1.0.0"},
            "instance": {
                "name": {"en": "Test Instance"},
                "entity": {"type": "city", "name": {"en": "Test City"}},
            },
            "contact": {"email": "test@example.com"},
            "localization": {
                "default_locale": "en",
                "supported_locales": ["en"],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name

        try:
            with patch.dict("os.environ", {"PLATFORM_CONFIG_PATH": temp_path}):
                clear_config_cache()
                config = load_platform_config()
                assert config.platform["name"] == "TestPlatform"
                assert config.instance.name["en"] == "Test Instance"
        finally:
            Path(temp_path).unlink()

    def test_load_default_when_file_missing(self):
        """Test fallback to default config when file is missing."""
        with patch.dict(
            "os.environ", {"PLATFORM_CONFIG_PATH": "/nonexistent/path.json"}
        ):
            clear_config_cache()
            config = load_platform_config()
            # Should return default Montreal config
            assert config.platform["name"] == "OpenCitiVibes"
            assert "Montreal" in config.instance.entity.name.get("en", "")

    def test_config_caching(self):
        """Test that config is cached."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_cache_clear(self):
        """Test cache clearing functionality."""
        config1 = get_config()
        clear_config_cache()
        config2 = get_config()
        # After cache clear, should reload (but result will be same default)
        assert config1 is not config2


class TestConfigHelpers:
    """Test helper functions."""

    def test_get_instance_name_english(self):
        """Test getting instance name in English."""
        name = get_instance_name("en")
        assert "Montreal" in name or "OpenCitiVibes" in name

    def test_get_instance_name_french(self):
        """Test getting instance name in French."""
        name = get_instance_name("fr")
        assert "Montréal" in name or "OpenCitiVibes" in name

    def test_get_instance_name_fallback(self):
        """Test instance name fallback for unknown locale."""
        name = get_instance_name("de")
        # Should fall back to English or return something
        assert len(name) > 0

    def test_get_entity_name_english(self):
        """Test getting entity name in English."""
        name = get_entity_name("en")
        assert name == "Montreal" or name == ""

    def test_get_entity_name_french(self):
        """Test getting entity name in French."""
        name = get_entity_name("fr")
        assert name == "Montréal" or name == ""


class TestPlatformConfigComplete:
    """Test complete PlatformConfig model."""

    def test_full_config_creation(self):
        """Test creating a complete PlatformConfig."""
        config = PlatformConfig(
            platform={"name": "OpenCitiVibes", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Test Platform"},
                entity=InstanceEntity(type="city", name={"en": "Test City"}),
            ),
            contact=ContactConfig(email="test@example.com"),
            legal=LegalConfig(
                jurisdiction={"en": "Test Jurisdiction"},
                courts={"en": "Test Courts"},
            ),
            branding=BrandingConfig(primary_color="#FF0000"),
            localization=LocalizationConfig(
                default_locale="en",
                supported_locales=["en", "fr"],
            ),
            features={"voting_enabled": True, "comments_enabled": True},
        )

        assert config.platform["name"] == "OpenCitiVibes"
        assert config.features["voting_enabled"] is True
        assert config.branding is not None
        assert config.branding.primary_color == "#FF0000"

    def test_config_optional_fields(self):
        """Test PlatformConfig with minimal required fields."""
        config = PlatformConfig(
            platform={"name": "Minimal"},
            instance=InstanceConfig(
                name={"en": "Min"},
                entity=InstanceEntity(type="community", name={"en": "Community"}),
            ),
            contact=ContactConfig(email="min@example.com"),
            localization=LocalizationConfig(),
        )

        assert config.legal is None
        assert config.branding is None
        assert config.features == {}
