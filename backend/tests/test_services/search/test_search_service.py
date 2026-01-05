"""Tests for main SearchService."""

import pytest
from unittest.mock import Mock, patch

from services.search import SearchService
from models.exceptions import ValidationException
from models.search_schemas import SearchResults, SearchFilters


class TestSearchServiceProperties:
    """Test service properties and initialization."""

    def test_clear_backend_cache(self) -> None:
        """Should clear the backend cache."""
        SearchService._backend_cache = Mock()  # Set a mock cache
        SearchService.clear_backend_cache()
        assert SearchService._backend_cache is None


class TestSearchIdeasValidation:
    """Test input validation for search_ideas."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_search_rejects_short_query(self) -> None:
        """Search should reject queries shorter than minimum."""
        mock_db = Mock()

        with pytest.raises(ValidationException) as exc_info:
            SearchService.search_ideas(mock_db, query="a")

        assert "at least" in str(exc_info.value.message).lower()

    def test_search_rejects_empty_query(self) -> None:
        """Search should reject empty queries."""
        mock_db = Mock()

        with pytest.raises(ValidationException) as exc_info:
            SearchService.search_ideas(mock_db, query="")

        assert "at least" in str(exc_info.value.message).lower()

    def test_search_rejects_whitespace_query(self) -> None:
        """Search should reject whitespace-only queries."""
        mock_db = Mock()

        with pytest.raises(ValidationException) as exc_info:
            SearchService.search_ideas(mock_db, query="   ")

        assert "at least" in str(exc_info.value.message).lower()

    def test_search_accepts_valid_query(self) -> None:
        """Search should accept valid queries."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.search_ideas.return_value = SearchResults(
            query="solar energy",
            total=0,
            results=[],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            result = SearchService.search_ideas(mock_db, query="solar energy")

        assert result is not None
        mock_backend.search_ideas.assert_called_once()


class TestSearchIdeasBackendSelection:
    """Test backend selection and availability."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_search_returns_empty_when_backend_unavailable(self) -> None:
        """Search should return empty results when backend not available."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = False
        mock_backend.backend_name = "sqlite_fts5"

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            result = SearchService.search_ideas(mock_db, query="test query")

        assert result.total == 0
        assert result.results == []
        assert result.search_backend == "sqlite_fts5"

    def test_search_caps_limit(self) -> None:
        """Search should cap limit to max results."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.search_ideas.return_value = SearchResults(
            query="test",
            total=0,
            results=[],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            SearchService.search_ideas(mock_db, query="test query", limit=500)

        # The search_query passed to backend should have capped limit
        call_args = mock_backend.search_ideas.call_args
        search_query = call_args[0][1]  # Second positional arg
        assert search_query.limit <= 100


class TestGetSuggestions:
    """Test suggestion retrieval."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_get_suggestions_returns_empty_for_short_query(self) -> None:
        """Suggestions should return empty list for short input."""
        mock_db = Mock()
        result = SearchService.get_suggestions(mock_db, "a")
        assert result == []

    def test_get_suggestions_returns_empty_for_empty_query(self) -> None:
        """Suggestions should return empty list for empty input."""
        mock_db = Mock()
        result = SearchService.get_suggestions(mock_db, "")
        assert result == []

    def test_get_suggestions_returns_empty_when_backend_unavailable(self) -> None:
        """Suggestions should return empty list when backend unavailable."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = False

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            result = SearchService.get_suggestions(mock_db, "solar")

        assert result == []

    def test_get_suggestions_caps_limit(self) -> None:
        """Suggestions should cap limit to 10."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.get_suggestions.return_value = ["test"]

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            SearchService.get_suggestions(mock_db, "test", limit=50)

        # Should be capped to 10
        mock_backend.get_suggestions.assert_called_once()
        call_args = mock_backend.get_suggestions.call_args
        assert call_args[0][2] <= 10


class TestBackendDetection:
    """Test backend detection from configuration."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_backend_detection_sqlite(self) -> None:
        """Should detect SQLite backend from URL."""
        mock_settings = Mock()
        mock_settings.get_search_backend.return_value = "sqlite_fts5"

        with patch(
            "services.search.search_service.get_settings", return_value=mock_settings
        ):
            SearchService.clear_backend_cache()
            backend = SearchService._get_backend()

        assert backend.backend_name == "sqlite_fts5"

    def test_backend_detection_postgresql(self) -> None:
        """Should detect PostgreSQL backend from URL."""
        mock_settings = Mock()
        mock_settings.get_search_backend.return_value = "postgresql_fts"

        with patch(
            "services.search.search_service.get_settings", return_value=mock_settings
        ):
            SearchService.clear_backend_cache()
            backend = SearchService._get_backend()

        assert backend.backend_name == "postgresql_fts"

    def test_backend_caching(self) -> None:
        """Backend should be cached after first call."""
        mock_settings = Mock()
        mock_settings.get_search_backend.return_value = "sqlite_fts5"

        with patch(
            "services.search.search_service.get_settings", return_value=mock_settings
        ):
            SearchService.clear_backend_cache()
            backend1 = SearchService._get_backend()
            backend2 = SearchService._get_backend()

        assert backend1 is backend2


class TestReindexIdea:
    """Test reindex operations."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_reindex_idea_calls_backend(self) -> None:
        """Reindex should call backend's reindex_idea method."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = True

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            SearchService.reindex_idea(mock_db, idea_id=123)

        mock_backend.reindex_idea.assert_called_once_with(mock_db, 123)

    def test_reindex_idea_skips_when_unavailable(self) -> None:
        """Reindex should skip when backend unavailable."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = False

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            SearchService.reindex_idea(mock_db, idea_id=123)

        mock_backend.reindex_idea.assert_not_called()


class TestRebuildIndex:
    """Test rebuild index operations."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_rebuild_index_calls_backend(self) -> None:
        """Rebuild should call backend's rebuild_index method."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.rebuild_index.return_value = 50

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            result = SearchService.rebuild_index(mock_db)

        assert result == 50
        mock_backend.rebuild_index.assert_called_once_with(mock_db)

    def test_rebuild_index_returns_zero_when_unavailable(self) -> None:
        """Rebuild should return 0 when backend unavailable."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = False

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            result = SearchService.rebuild_index(mock_db)

        assert result == 0
        mock_backend.rebuild_index.assert_not_called()


class TestGetBackendInfo:
    """Test backend info retrieval."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_get_backend_info_returns_dict(self) -> None:
        """Backend info should return dict with name and availability."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.backend_name = "sqlite_fts5"
        mock_backend.is_available.return_value = True

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            result = SearchService.get_backend_info(mock_db)

        assert result.backend == "sqlite_fts5"
        assert result.available is True


class TestSearchByTag:
    """Test tag-based search (Phase 3)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_search_by_tag_returns_results(self) -> None:
        """Should return search results for matching tags."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.backend_name = "sqlite_fts5"

        # Mock tag repository at the import location
        mock_repo = Mock()
        mock_repo.search_tags.return_value = []  # No tags found

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            with patch(
                "repositories.tag_repository.TagRepository", return_value=mock_repo
            ):
                result = SearchService.search_by_tag(mock_db, tag_query="solar")

        assert result.query == "#solar"
        assert result.total == 0

    def test_search_by_tag_empty_results_when_no_tags(self) -> None:
        """Should return empty results when no matching tags."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.backend_name = "sqlite_fts5"

        mock_repo = Mock()
        mock_repo.search_tags.return_value = []

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            with patch(
                "repositories.tag_repository.TagRepository", return_value=mock_repo
            ):
                result = SearchService.search_by_tag(mock_db, tag_query="nonexistent")

        assert result.total == 0
        assert result.results == []


class TestSearchWithTags:
    """Test combined idea and tag search (Phase 3)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_search_with_tags_hashtag_query(self) -> None:
        """Query starting with # should search tags only."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.backend_name = "sqlite_fts5"

        mock_repo = Mock()
        mock_repo.search_tags.return_value = []

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            with patch(
                "repositories.tag_repository.TagRepository", return_value=mock_repo
            ):
                result = SearchService.search_with_tags(mock_db, query="#solar")

        assert "ideas" in result
        assert "matching_tags" in result
        assert result["ideas"].query == "#solar"


class TestGetAutocomplete:
    """Test combined autocomplete (Phase 3)."""

    @pytest.fixture(autouse=True)
    def clear_cache(self) -> None:
        """Clear backend cache before each test."""
        SearchService.clear_backend_cache()

    def test_get_autocomplete_short_query(self) -> None:
        """Short query should return empty results."""
        mock_db = Mock()
        result = SearchService.get_autocomplete(mock_db, "a")

        assert result["ideas"] == []
        assert result["tags"] == []
        assert result["queries"] == []

    def test_get_autocomplete_returns_structure(self) -> None:
        """Should return dict with ideas, tags, queries."""
        mock_db = Mock()
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.get_suggestions.return_value = ["Solar Panel"]

        mock_repo = Mock()
        mock_repo.search_tags.return_value = []

        with patch.object(SearchService, "_get_backend", return_value=mock_backend):
            with patch(
                "repositories.tag_repository.TagRepository", return_value=mock_repo
            ):
                result = SearchService.get_autocomplete(mock_db, "solar")

        assert "ideas" in result
        assert "tags" in result
        assert "queries" in result
        assert result["ideas"] == ["Solar Panel"]
