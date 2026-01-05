"""Platform configuration service.

Loads and provides access to instance-specific configuration.
"""

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, field_validator


# Regex for hex color validation
_HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class InstanceEntity(BaseModel):
    """Entity being served (city, organization, etc.)."""

    type: str  # city, region, country, organization, community
    name: dict[str, str]  # {"en": "Montreal", "fr": "Montréal"}
    region: dict[str, str] | None = None
    country: dict[str, str] | None = None


class InstanceConfig(BaseModel):
    """Instance-specific configuration."""

    name: dict[str, str]  # {"en": "Ideas for Montreal", "fr": "Idées pour Montréal"}
    entity: InstanceEntity
    location: dict[str, Any] | None = None


class ContactConfig(BaseModel):
    """Contact information."""

    email: str
    support_email: str | None = None
    address: dict[str, str] | None = None


class LegalConfig(BaseModel):
    """Legal jurisdiction configuration."""

    jurisdiction: dict[str, str]
    courts: dict[str, str]
    privacy_authority: dict[str, Any] | None = None
    data_protection_laws: list[dict[str, Any]] = []


class LocalizationConfig(BaseModel):
    """Localization settings."""

    default_locale: str = "en"
    supported_locales: list[str] = ["en"]
    date_format: dict[str, str] | None = None


BorderRadiusPreset = Literal["none", "sm", "md", "lg", "full"]


class BrandingConfig(BaseModel):
    """Visual branding configuration for platform customization.

    Supports extended theming with colors, typography, dark mode, and images.
    All new fields are optional for backward compatibility.
    """

    # ===========================================
    # Existing fields (backward compatible)
    # ===========================================
    primary_color: str = "#0066CC"
    secondary_color: str = "#003366"
    hero_image: str | None = None
    logo: str | None = None

    # ===========================================
    # Extended colors (new - all optional)
    # ===========================================
    primary_dark: str | None = None  # Auto-darken from primary if not provided
    accent: str | None = None  # Default: #14b8a6 (teal)
    success: str | None = None  # Default: #22c55e (green)
    warning: str | None = None  # Default: #eab308 (yellow)
    error: str | None = None  # Default: #ef4444 (red)

    # ===========================================
    # Dark mode overrides (new)
    # ===========================================
    dark_mode: dict[str, str] | None = None
    # Example: {"primary": "#4a9eff", "background": "#0f172a", "surface": "#1e293b"}

    # ===========================================
    # Typography (new)
    # ===========================================
    fonts: dict[str, str] | None = None
    # Example: {"heading": "Poppins", "body": "Inter"}
    font_url: str | None = None
    # Example: "https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&display=swap"

    # ===========================================
    # Border radius preset (new)
    # ===========================================
    border_radius: BorderRadiusPreset | None = None

    # ===========================================
    # Extended images (new)
    # ===========================================
    logo_dark: str | None = None  # Logo for dark mode
    favicon: str | None = None  # Custom favicon path
    og_image: str | None = None  # Open Graph image for social sharing

    # ===========================================
    # Hero customization (new)
    # ===========================================
    hero_overlay: bool = True  # Show gradient overlay on hero image
    hero_subtitle: dict[str, str] | None = None  # Custom subtitle for hero banner
    hero_position: str | None = (
        None  # CSS object-position (e.g., "top", "center", "bottom")
    )

    @field_validator(
        "primary_color",
        "secondary_color",
        "primary_dark",
        "accent",
        "success",
        "warning",
        "error",
        mode="before",
    )
    @classmethod
    def validate_hex_color(cls, v: str | None) -> str | None:
        """Validate hex color format (#RRGGBB)."""
        if v is None:
            return None
        if not _HEX_COLOR_PATTERN.match(v):
            raise ValueError(f"Invalid hex color format: {v}. Expected #RRGGBB.")
        return v

    @field_validator("dark_mode", mode="before")
    @classmethod
    def validate_dark_mode_colors(
        cls, v: dict[str, str] | None
    ) -> dict[str, str] | None:
        """Validate all colors in dark_mode dict."""
        if v is None:
            return None
        for key, color in v.items():
            if not _HEX_COLOR_PATTERN.match(color):
                raise ValueError(
                    f"Invalid hex color in dark_mode['{key}']: {color}. Expected #RRGGBB."
                )
        return v


class PlatformConfig(BaseModel):
    """Complete platform configuration."""

    platform: dict[str, Any]
    instance: InstanceConfig
    contact: ContactConfig
    legal: LegalConfig | None = None
    branding: BrandingConfig | None = None
    localization: LocalizationConfig
    features: dict[str, bool] = {}


@lru_cache(maxsize=1)
def load_platform_config() -> PlatformConfig:
    """Load platform configuration from file or environment.

    Returns:
        PlatformConfig: Parsed and validated configuration.

    Raises:
        FileNotFoundError: If config file not found and no defaults available.
        ValidationError: If config is invalid.
    """
    config_path = os.getenv(
        "PLATFORM_CONFIG_PATH",
        str(Path(__file__).parent.parent / "config" / "platform.config.json"),
    )

    config_file = Path(config_path)

    if not config_file.exists():
        # Return default config for backwards compatibility
        return _get_default_config()

    with open(config_file, encoding="utf-8") as f:
        data = json.load(f)

    return PlatformConfig(**data)


def _get_default_config() -> PlatformConfig:
    """Default configuration for backwards compatibility with Montreal instance."""
    return PlatformConfig(
        platform={"name": "OpenCitiVibes", "version": "1.0.0"},
        instance=InstanceConfig(
            name={"en": "Ideas for Montreal", "fr": "Idées pour Montréal"},
            entity=InstanceEntity(
                type="city",
                name={"en": "Montreal", "fr": "Montréal"},
                region={"en": "Quebec", "fr": "Québec"},
                country={"en": "Canada", "fr": "Canada"},
            ),
            location={
                "display": {"en": "Montreal, Quebec", "fr": "Montréal, Québec"},
                "timezone": "America/Montreal",
            },
        ),
        contact=ContactConfig(
            email="contact@idees-montreal.ca",
            support_email="support@idees-montreal.ca",
        ),
        legal=LegalConfig(
            jurisdiction={"en": "Quebec and Canada", "fr": "Québec et Canada"},
            courts={
                "en": "competent courts of Quebec",
                "fr": "tribunaux compétents du Québec",
            },
        ),
        localization=LocalizationConfig(
            default_locale="fr",
            supported_locales=["fr", "en"],
        ),
        branding=BrandingConfig(
            primary_color="#0066CC",
            secondary_color="#003366",
            hero_image="/images/hero/montreal-skyline.jpg",
        ),
    )


def get_config() -> PlatformConfig:
    """Get the current platform configuration."""
    return load_platform_config()


def get_instance_name(locale: str = "en") -> str:
    """Get localized instance name."""
    config = get_config()
    return config.instance.name.get(
        locale, config.instance.name.get("en", "OpenCitiVibes")
    )


def get_entity_name(locale: str = "en") -> str:
    """Get localized entity name (city/org name)."""
    config = get_config()
    return config.instance.entity.name.get(locale, "")


def clear_config_cache() -> None:
    """Clear the configuration cache.

    Useful for testing or when configuration changes at runtime.
    """
    load_platform_config.cache_clear()
