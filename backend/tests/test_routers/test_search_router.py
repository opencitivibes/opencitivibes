"""Integration tests for search API endpoints."""

from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from models.search_schemas import (
    SearchResults,
    SearchResultItem,
    SearchFilters,
    SearchHighlight,
)
from models.schemas import IdeaWithScore


class TestSearchIdeasEndpoint:
    """Integration tests for GET /api/search/ideas endpoint."""

    def test_search_returns_200_with_valid_query(self, client: TestClient) -> None:
        """Search should return 200 with valid query."""
        # Mock the SearchService to avoid FTS table dependency
        mock_results = SearchResults(
            query="test",
            total=0,
            results=[],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get("/api/search/ideas?q=test")

        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert "total" in data
        assert "results" in data

    def test_search_validates_query_length(self, client: TestClient) -> None:
        """Search should reject queries shorter than 2 chars."""
        response = client.get("/api/search/ideas?q=a")

        assert response.status_code == 422

    def test_search_rejects_empty_query(self, client: TestClient) -> None:
        """Search should reject empty queries."""
        response = client.get("/api/search/ideas?q=")

        assert response.status_code == 422

    def test_search_with_category_filter(self, client: TestClient) -> None:
        """Search should accept category filter."""
        mock_results = SearchResults(
            query="test",
            total=0,
            results=[],
            filters_applied=SearchFilters(category_id=1),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get("/api/search/ideas?q=test&category_id=1")

        assert response.status_code == 200

    def test_search_with_status_filter(self, client: TestClient) -> None:
        """Search should accept status filter."""
        mock_results = SearchResults(
            query="test",
            total=0,
            results=[],
            filters_applied=SearchFilters(status="PENDING"),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get("/api/search/ideas?q=test&status=PENDING")

        assert response.status_code == 200

    def test_search_with_language_filter(self, client: TestClient) -> None:
        """Search should accept language filter (en/fr)."""
        mock_results = SearchResults(
            query="test",
            total=0,
            results=[],
            filters_applied=SearchFilters(language="fr"),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get("/api/search/ideas?q=test&language=fr")

        assert response.status_code == 200

    def test_search_rejects_invalid_language(self, client: TestClient) -> None:
        """Search should reject invalid language values."""
        response = client.get("/api/search/ideas?q=test&language=invalid")

        assert response.status_code == 422

    def test_search_with_pagination(self, client: TestClient) -> None:
        """Search should accept pagination parameters."""
        mock_results = SearchResults(
            query="test",
            total=50,
            results=[],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get("/api/search/ideas?q=test&skip=10&limit=20")

        assert response.status_code == 200

    def test_search_with_sort_order(self, client: TestClient) -> None:
        """Search should accept sort order parameter."""
        mock_results = SearchResults(
            query="test",
            total=0,
            results=[],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get("/api/search/ideas?q=test&sort=date_desc")

        assert response.status_code == 200

    def test_search_with_highlight_disabled(self, client: TestClient) -> None:
        """Search should accept highlight=false parameter."""
        mock_results = SearchResults(
            query="test",
            total=0,
            results=[],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get("/api/search/ideas?q=test&highlight=false")

        assert response.status_code == 200

    def test_search_with_phase3_filters(self, client: TestClient) -> None:
        """Search should accept Phase 3 enhanced filters."""
        mock_results = SearchResults(
            query="test",
            total=0,
            results=[],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get(
                "/api/search/ideas?q=test"
                "&category_ids=1&category_ids=2"
                "&tag_names=solar&tag_names=energy"
                "&min_score=5"
                "&has_comments=true"
                "&exclude_ids=10&exclude_ids=20"
            )

        assert response.status_code == 200


class TestSuggestionsEndpoint:
    """Integration tests for GET /api/search/suggestions endpoint."""

    def test_suggestions_returns_list(self, client: TestClient) -> None:
        """Suggestions should return a list."""
        with patch("routers.search_router.SearchService") as MockService:
            MockService.get_suggestions.return_value = ["solar", "solar panel"]
            response = client.get("/api/search/suggestions?q=so")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_suggestions_validates_query_length(self, client: TestClient) -> None:
        """Suggestions should reject queries shorter than 2 chars."""
        response = client.get("/api/search/suggestions?q=a")

        assert response.status_code == 422

    def test_suggestions_respects_limit(self, client: TestClient) -> None:
        """Suggestions should respect limit parameter."""
        with patch("routers.search_router.SearchService") as MockService:
            MockService.get_suggestions.return_value = ["test1", "test2", "test3"]
            response = client.get("/api/search/suggestions?q=test&limit=3")

        assert response.status_code == 200

    def test_suggestions_rejects_high_limit(self, client: TestClient) -> None:
        """Suggestions should reject limit > 10."""
        response = client.get("/api/search/suggestions?q=test&limit=20")

        assert response.status_code == 422


class TestSearchInfoEndpoint:
    """Integration tests for GET /api/search/info endpoint."""

    def test_info_returns_backend_status(self, client: TestClient) -> None:
        """Info should return backend name and availability."""
        with patch("routers.search_router.SearchService") as MockService:
            MockService.get_backend_info.return_value = {
                "backend": "sqlite_fts5",
                "available": True,
            }
            response = client.get("/api/search/info")

        assert response.status_code == 200
        data = response.json()
        assert "backend" in data
        assert "available" in data


class TestReindexEndpoint:
    """Integration tests for POST /api/search/reindex/{idea_id} endpoint."""

    def test_reindex_requires_admin(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Reindex should require admin authentication."""
        response = client.post("/api/search/reindex/1", headers=auth_headers)

        # Should be forbidden for regular user
        assert response.status_code == 403

    def test_reindex_works_for_admin(
        self, client: TestClient, admin_auth_headers: dict
    ) -> None:
        """Reindex should work for admin user."""
        with patch("routers.search_router.SearchService") as MockService:
            MockService.reindex_idea.return_value = None
            response = client.post("/api/search/reindex/1", headers=admin_auth_headers)

        assert response.status_code == 204


class TestRebuildIndexEndpoint:
    """Integration tests for POST /api/search/rebuild endpoint."""

    def test_rebuild_requires_admin(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """Rebuild should require admin authentication."""
        response = client.post("/api/search/rebuild", headers=auth_headers)

        # Should be forbidden for regular user
        assert response.status_code == 403

    def test_rebuild_works_for_admin(
        self, client: TestClient, admin_auth_headers: dict
    ) -> None:
        """Rebuild should work for admin user."""
        with patch("routers.search_router.SearchService") as MockService:
            MockService.rebuild_index.return_value = 50
            response = client.post("/api/search/rebuild", headers=admin_auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["indexed"] == 50


class TestAutocompleteEndpoint:
    """Integration tests for GET /api/search/autocomplete endpoint (Phase 3)."""

    def test_autocomplete_returns_structure(self, client: TestClient) -> None:
        """Autocomplete should return ideas, tags, and queries."""
        with patch("routers.search_router.SearchService") as MockService:
            MockService.get_autocomplete.return_value = {
                "ideas": ["Solar Panel"],
                "tags": [],
                "queries": [],
            }
            response = client.get("/api/search/autocomplete?q=so")

        assert response.status_code == 200
        data = response.json()
        assert "ideas" in data
        assert "tags" in data
        assert "queries" in data

    def test_autocomplete_validates_query_length(self, client: TestClient) -> None:
        """Autocomplete should reject queries shorter than 2 chars."""
        response = client.get("/api/search/autocomplete?q=a")

        assert response.status_code == 422


class TestSearchWithTagsEndpoint:
    """Integration tests for GET /api/search/with-tags endpoint (Phase 3)."""

    def test_search_with_tags_returns_structure(self, client: TestClient) -> None:
        """Search with tags should return ideas and matching_tags."""
        mock_results = SearchResults(
            query="solar",
            total=0,
            results=[],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_with_tags.return_value = {
                "ideas": mock_results,
                "matching_tags": [],
            }
            response = client.get("/api/search/with-tags?q=solar")

        assert response.status_code == 200
        data = response.json()
        assert "ideas" in data
        assert "matching_tags" in data

    def test_search_with_tags_validates_query_length(self, client: TestClient) -> None:
        """Search with tags should reject queries shorter than 2 chars."""
        response = client.get("/api/search/with-tags?q=a")

        assert response.status_code == 422

    def test_search_with_tags_with_hashtag(self, client: TestClient) -> None:
        """Query starting with # should search tags only."""
        mock_results = SearchResults(
            query="#solar",
            total=0,
            results=[],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_with_tags.return_value = {
                "ideas": mock_results,
                "matching_tags": [],
            }
            response = client.get("/api/search/with-tags?q=%23solar")

        assert response.status_code == 200


class TestSearchResponseFormat:
    """Test search response format and structure."""

    def test_search_result_includes_required_fields(self, client: TestClient) -> None:
        """Search results should include all required fields."""
        mock_results = SearchResults(
            query="test",
            total=1,
            results=[],
            filters_applied=SearchFilters(status="APPROVED"),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get("/api/search/ideas?q=test")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "query" in data
        assert data["query"] == "test"
        assert "total" in data
        assert data["total"] == 1
        assert "results" in data
        assert isinstance(data["results"], list)
        assert "filters_applied" in data
        assert "search_backend" in data
        assert data["search_backend"] == "sqlite_fts5"

    def test_search_result_item_format(self, client: TestClient) -> None:
        """Individual search result should have correct format."""
        from datetime import datetime, timezone

        mock_idea = Mock(spec=IdeaWithScore)
        mock_idea.id = 1
        mock_idea.title = "Test Idea"
        mock_idea.description = "Test description"
        mock_idea.status = "approved"
        mock_idea.score = 10
        mock_idea.upvotes = 15
        mock_idea.downvotes = 5
        mock_idea.comment_count = 3
        mock_idea.created_at = datetime.now(timezone.utc)
        mock_idea.updated_at = None
        mock_idea.user_id = 1
        mock_idea.category_id = 1
        mock_idea.author = Mock()
        mock_idea.category = Mock()
        mock_idea.tags = []
        mock_idea.current_user_vote = None

        mock_result = SearchResultItem(
            idea=mock_idea,
            relevance_score=0.95,
            highlights=SearchHighlight(
                title="<mark>Test</mark> Idea",
                description="<mark>Test</mark> description",
            ),
        )

        mock_results = SearchResults(
            query="test",
            total=1,
            results=[mock_result],
            filters_applied=SearchFilters(),
            search_backend="sqlite_fts5",
        )

        with patch("routers.search_router.SearchService") as MockService:
            MockService.search_ideas.return_value = mock_results
            response = client.get("/api/search/ideas?q=test")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1

        result_item = data["results"][0]
        assert "idea" in result_item
        assert "relevance_score" in result_item
        assert result_item["relevance_score"] == 0.95
        assert "highlights" in result_item
