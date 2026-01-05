"""Unit tests for generate_test_data.py helper functions."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from services.config_service import (  # noqa: E402
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


class TestGetAdminEmailDomain:
    """Tests for _get_admin_email_domain function."""

    def test_extracts_domain_from_contact_email(self):
        """Should extract domain from contact email in config."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Test"},
                entity=InstanceEntity(type="city", name={"en": "City"}),
            ),
            contact=ContactConfig(email="contact@custom-domain.com"),
            localization=LocalizationConfig(default_locale="en"),
        )

        with patch("scripts.generate_test_data.get_config", return_value=mock_config):
            from scripts.generate_test_data import _get_admin_email_domain

            domain = _get_admin_email_domain()

        assert domain == "custom-domain.com"

    def test_fallback_on_exception(self):
        """Should return fallback domain on exception."""
        with patch(
            "scripts.generate_test_data.get_config",
            side_effect=Exception("Config error"),
        ):
            from scripts.generate_test_data import _get_admin_email_domain

            domain = _get_admin_email_domain()

        assert domain == "opencitivibes.local"

    def test_fallback_on_missing_at_symbol(self):
        """Should return fallback if email has no @ symbol."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Test"},
                entity=InstanceEntity(type="city", name={"en": "City"}),
            ),
            contact=ContactConfig(email="invalid-email"),  # No @ symbol
            localization=LocalizationConfig(default_locale="en"),
        )

        with patch("scripts.generate_test_data.get_config", return_value=mock_config):
            from scripts.generate_test_data import _get_admin_email_domain

            domain = _get_admin_email_domain()

        assert domain == "opencitivibes.local"


class TestGetTestAdminEmail:
    """Tests for _get_test_admin_email function."""

    def test_generates_indexed_admin_email(self):
        """Should generate admin{index}@{domain} format."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Test"},
                entity=InstanceEntity(type="city", name={"en": "City"}),
            ),
            contact=ContactConfig(email="contact@test-domain.com"),
            localization=LocalizationConfig(default_locale="en"),
        )

        with patch("scripts.generate_test_data.get_config", return_value=mock_config):
            from scripts.generate_test_data import _get_test_admin_email

            email1 = _get_test_admin_email(1)
            email2 = _get_test_admin_email(5)

        assert email1 == "admin1@test-domain.com"
        assert email2 == "admin5@test-domain.com"


class TestGetTestCategoryAdminEmail:
    """Tests for _get_test_category_admin_email function."""

    def test_generates_indexed_catadmin_email(self):
        """Should generate catadmin{index}@{domain} format."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Test"},
                entity=InstanceEntity(type="city", name={"en": "City"}),
            ),
            contact=ContactConfig(email="contact@myplatform.org"),
            localization=LocalizationConfig(default_locale="en"),
        )

        with patch("scripts.generate_test_data.get_config", return_value=mock_config):
            from scripts.generate_test_data import _get_test_category_admin_email

            email1 = _get_test_category_admin_email(1)
            email3 = _get_test_category_admin_email(3)

        assert email1 == "catadmin1@myplatform.org"
        assert email3 == "catadmin3@myplatform.org"


class TestDatabasePathNaming:
    """Tests for database path naming convention."""

    def test_get_db_path_uses_opencitivibes(self):
        """get_db_path should use opencitivibes naming."""
        from scripts.generate_test_data import get_db_path

        small_path = get_db_path("small")
        medium_path = get_db_path("medium")
        large_path = get_db_path("large")

        assert "opencitivibes_test_small.db" in str(small_path)
        assert "opencitivibes_test_medium.db" in str(medium_path)
        assert "opencitivibes_test_large.db" in str(large_path)

    def test_test_db_path_uses_opencitivibes(self):
        """TEST_DB_PATH should use opencitivibes naming."""
        from scripts.generate_test_data import TEST_DB_PATH

        assert "opencitivibes" in str(TEST_DB_PATH)
