"""Unit tests for similar ideas stopwords functionality."""

from unittest.mock import patch

import pytest

from services.config_service import (
    ContactConfig,
    InstanceConfig,
    InstanceEntity,
    LocalizationConfig,
    PlatformConfig,
    clear_config_cache,
)
from services.similar_ideas import SimilarIdeasService, _get_entity_stopwords


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear config cache before each test."""
    clear_config_cache()
    yield
    clear_config_cache()


class TestGetEntityStopwords:
    """Tests for _get_entity_stopwords function."""

    def test_returns_entity_names_in_all_locales(self):
        """Should return entity names in all supported locales."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Ideas for TestCity", "fr": "Idées pour VilleTest"},
                entity=InstanceEntity(
                    type="city",
                    name={"en": "TestCity", "fr": "VilleTest"},
                ),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="en",
                supported_locales=["en", "fr"],
            ),
        )

        with patch("services.similar_ideas.get_config", return_value=mock_config):
            stopwords = _get_entity_stopwords()

        assert "testcity" in stopwords
        assert "villetest" in stopwords

    def test_includes_region_names(self):
        """Should include region names when present."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Test Platform"},
                entity=InstanceEntity(
                    type="city",
                    name={"en": "Montreal"},
                    region={"en": "Quebec", "fr": "Québec"},
                ),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="en",
                supported_locales=["en", "fr"],
            ),
        )

        with patch("services.similar_ideas.get_config", return_value=mock_config):
            stopwords = _get_entity_stopwords()

        assert "quebec" in stopwords
        assert "québec" in stopwords

    def test_includes_instance_name_words(self):
        """Should include words from instance name."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Ideas for Montreal"},
                entity=InstanceEntity(
                    type="city",
                    name={"en": "Montreal"},
                ),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="en",
                supported_locales=["en"],
            ),
        )

        with patch("services.similar_ideas.get_config", return_value=mock_config):
            stopwords = _get_entity_stopwords()

        # Should include full name and individual words > 2 chars
        assert "ideas for montreal" in stopwords
        assert "ideas" in stopwords
        assert "montreal" in stopwords
        # "for" is only 3 chars, should be included
        assert "for" in stopwords

    def test_handles_empty_entity_name(self):
        """Should handle empty entity names gracefully."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Test"},
                entity=InstanceEntity(
                    type="community",
                    name={},  # Empty name dict
                ),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="en",
                supported_locales=["en"],
            ),
        )

        with patch("services.similar_ideas.get_config", return_value=mock_config):
            stopwords = _get_entity_stopwords()

        # Should return a set (possibly empty for entity names)
        assert isinstance(stopwords, set)

    def test_returns_lowercase_values(self):
        """Should return all stopwords in lowercase."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Ideas for UPPERCASE"},
                entity=InstanceEntity(
                    type="city",
                    name={"en": "UPPERCASE", "fr": "MixedCase"},
                ),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="en",
                supported_locales=["en", "fr"],
            ),
        )

        with patch("services.similar_ideas.get_config", return_value=mock_config):
            stopwords = _get_entity_stopwords()

        # All values should be lowercase
        for word in stopwords:
            assert word == word.lower(), f"'{word}' is not lowercase"


class TestSimilarIdeasServiceStopwords:
    """Tests for SimilarIdeasService stopword integration."""

    def test_service_includes_entity_stopwords(self):
        """Service should include entity-specific stopwords."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Test Platform"},
                entity=InstanceEntity(
                    type="city",
                    name={"en": "CustomCity"},
                ),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="en",
                supported_locales=["en"],
            ),
        )

        with patch("services.similar_ideas.get_config", return_value=mock_config):
            service = SimilarIdeasService()

        # Should include base domain stopwords
        assert "ville" in service._domain_stop_words
        assert "city" in service._domain_stop_words
        assert "idée" in service._domain_stop_words
        assert "idea" in service._domain_stop_words

        # Should include entity-specific stopword
        assert "customcity" in service._domain_stop_words

    def test_extract_keywords_excludes_entity_stopwords(self):
        """extract_keywords should exclude entity-specific words."""
        mock_config = PlatformConfig(
            platform={"name": "Test", "version": "1.0.0"},
            instance=InstanceConfig(
                name={"en": "Test Platform"},
                entity=InstanceEntity(
                    type="city",
                    name={"en": "TestVille"},
                ),
            ),
            contact=ContactConfig(email="test@example.com"),
            localization=LocalizationConfig(
                default_locale="en",
                supported_locales=["en"],
            ),
        )

        with patch("services.similar_ideas.get_config", return_value=mock_config):
            service = SimilarIdeasService()

        text = "Improve transportation in TestVille with better buses"
        keywords = service.extract_keywords(text, "en")

        # Should NOT include the entity name (TestVille)
        assert "testville" not in keywords

        # Should include other meaningful words
        assert "improve" in keywords
        assert "transportation" in keywords
        assert "better" in keywords
        assert "buses" in keywords

    def test_service_combines_base_and_entity_stopwords(self):
        """Service should combine BASE_DOMAIN_STOP_WORDS with entity stopwords."""
        service = SimilarIdeasService()

        # Base stopwords should always be present
        assert "ville" in service._domain_stop_words
        assert "city" in service._domain_stop_words
        assert "projet" in service._domain_stop_words
        assert "project" in service._domain_stop_words

        # Entity stopwords come from config (Montreal for default)
        # The actual values depend on the default config
        assert isinstance(service._domain_stop_words, set)
        assert len(service._domain_stop_words) >= len(service.BASE_DOMAIN_STOP_WORDS)
