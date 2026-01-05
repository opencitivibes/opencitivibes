"""Tests for SQLite FTS5 search backend."""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from services.search.sqlite_fts5_backend import SQLiteFTS5Backend
from models.search_schemas import (
    SearchQuery,
    SearchFilters,
    SearchSortOrder,
)


class TestSQLiteFTS5BackendProperties:
    """Test backend properties and basic functionality."""

    @pytest.fixture
    def backend(self) -> SQLiteFTS5Backend:
        """Create backend instance."""
        return SQLiteFTS5Backend()

    def test_backend_name(self, backend: SQLiteFTS5Backend) -> None:
        """Backend should return correct name."""
        assert backend.backend_name == "sqlite_fts5"

    def test_fts_table_name(self, backend: SQLiteFTS5Backend) -> None:
        """Backend should have correct FTS table name."""
        assert backend.FTS_TABLE_NAME == "ideas_fts"


class TestBuildFtsQuery:
    """Test FTS query building."""

    @pytest.fixture
    def backend(self) -> SQLiteFTS5Backend:
        """Create backend instance."""
        return SQLiteFTS5Backend()

    def test_build_fts_query_single_word(self, backend: SQLiteFTS5Backend) -> None:
        """Single word should get prefix matching."""
        query = backend._build_fts_query("solar")
        assert query == "solar*"

    def test_build_fts_query_multiple_words(self, backend: SQLiteFTS5Backend) -> None:
        """Multiple words should be OR'd with prefix on last."""
        query = backend._build_fts_query("solar energy")
        assert "solar" in query
        assert "energy*" in query
        assert "OR" in query

    def test_build_fts_query_empty(self, backend: SQLiteFTS5Backend) -> None:
        """Empty query should return empty string."""
        query = backend._build_fts_query("")
        assert query == ""

    def test_build_fts_query_whitespace_only(self, backend: SQLiteFTS5Backend) -> None:
        """Whitespace-only query should return empty string."""
        query = backend._build_fts_query("   ")
        assert query == ""

    def test_build_fts_query_short_words_filtered(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Words shorter than 2 characters should be filtered."""
        query = backend._build_fts_query("a b solar")
        # Only 'solar' should remain
        assert "solar*" in query
        assert query.count("OR") == 0  # No OR because only one word

    def test_build_fts_query_three_words(self, backend: SQLiteFTS5Backend) -> None:
        """Three words should have correct OR structure."""
        query = backend._build_fts_query("solar energy project")
        assert "solar" in query
        assert "energy" in query
        assert "project*" in query
        # Should have 2 ORs for 3 terms
        assert query.count("OR") == 2


class TestIsAvailable:
    """Test backend availability checks."""

    @pytest.fixture
    def backend(self) -> SQLiteFTS5Backend:
        """Create backend instance."""
        return SQLiteFTS5Backend()

    def test_is_available_returns_true_when_table_exists(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """is_available should return True when FTS table exists."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = ("ideas_fts",)
        mock_db.execute.return_value = mock_result

        assert backend.is_available(mock_db) is True

    def test_is_available_returns_false_when_no_table(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """is_available should return False when FTS table missing."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        mock_db.execute.return_value = mock_result

        assert backend.is_available(mock_db) is False

    def test_is_available_returns_false_on_exception(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """is_available should return False on database error."""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("Database error")

        assert backend.is_available(mock_db) is False


class TestGenerateHighlights:
    """Test highlight generation."""

    @pytest.fixture
    def backend(self) -> SQLiteFTS5Backend:
        """Create backend instance."""
        return SQLiteFTS5Backend()

    def test_generate_highlights_marks_matches(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Highlights should wrap matches in <mark> tags."""
        highlights = backend._generate_highlights(
            "solar", "Solar Panel Initiative", "Install solar panels on buildings"
        )

        assert highlights.title is not None
        assert "<mark>" in highlights.title
        assert highlights.description is not None
        assert "<mark>" in highlights.description

    def test_generate_highlights_case_insensitive(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Highlighting should be case-insensitive."""
        highlights = backend._generate_highlights(
            "solar", "SOLAR Panel Initiative", "Install solar panels"
        )

        assert highlights.title is not None
        assert "<mark>" in highlights.title
        # Both SOLAR and solar should be highlighted

    def test_generate_highlights_escapes_html(self, backend: SQLiteFTS5Backend) -> None:
        """Highlights should escape existing HTML to prevent XSS."""
        highlights = backend._generate_highlights(
            "test", "Test <script>alert('xss')</script>", "Description"
        )

        assert highlights.title is not None
        # Script tag should be escaped
        assert "<script>" not in highlights.title
        assert "&lt;script&gt;" in highlights.title

    def test_generate_highlights_with_none_description(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Highlights should handle None description."""
        highlights = backend._generate_highlights("solar", "Solar Panel", None)

        assert highlights.title is not None
        assert "<mark>" in highlights.title
        assert highlights.description is None

    def test_generate_highlights_multiple_matches(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Multiple matches should all be highlighted."""
        highlights = backend._generate_highlights(
            "solar",
            "Solar panels",
            "Solar energy from solar panels is great for solar power",
        )

        assert highlights.description is not None
        # Multiple occurrences should be highlighted
        assert highlights.description.count("<mark>") >= 1


class TestBuildFilterClause:
    """Test filter clause building."""

    @pytest.fixture
    def backend(self) -> SQLiteFTS5Backend:
        """Create backend instance."""
        return SQLiteFTS5Backend()

    def test_build_filter_clause_default_status(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Should include APPROVED status by default."""
        filters = SearchFilters()
        clauses, params = backend._build_filter_clause(filters)

        assert "i.status = :status" in clauses
        assert params["status"] == "APPROVED"

    def test_build_filter_clause_with_category(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Should add category filter when specified."""
        filters = SearchFilters(category_id=5)
        clauses, params = backend._build_filter_clause(filters)

        assert any("category_id" in clause for clause in clauses)
        assert params["category_id"] == 5

    def test_build_filter_clause_with_multiple_categories(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Should add multiple category filter (Phase 3)."""
        filters = SearchFilters(category_ids=[1, 2, 3])
        clauses, params = backend._build_filter_clause(filters)

        assert any("IN" in clause for clause in clauses)
        assert params["cat_0"] == 1
        assert params["cat_1"] == 2
        assert params["cat_2"] == 3

    def test_build_filter_clause_with_author(self, backend: SQLiteFTS5Backend) -> None:
        """Should add author filter when specified."""
        filters = SearchFilters(author_id=10)
        clauses, params = backend._build_filter_clause(filters)

        assert any("user_id" in clause for clause in clauses)
        assert params["author_id"] == 10

    def test_build_filter_clause_with_date_range(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Should add date range filters when specified."""
        from_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        to_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
        filters = SearchFilters(from_date=from_date, to_date=to_date)
        clauses, params = backend._build_filter_clause(filters)

        assert any("created_at >=" in clause for clause in clauses)
        assert any("created_at <=" in clause for clause in clauses)
        assert params["from_date"] == from_date
        assert params["to_date"] == to_date

    def test_build_filter_clause_with_exclude_ids(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Should exclude specific IDs (Phase 3)."""
        filters = SearchFilters(exclude_ids=[1, 2, 3])
        clauses, params = backend._build_filter_clause(filters)

        assert any("NOT IN" in clause for clause in clauses)
        assert params["excl_0"] == 1
        assert params["excl_1"] == 2
        assert params["excl_2"] == 3

    def test_build_filter_clause_with_min_score(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Should add minimum score filter (Phase 3)."""
        filters = SearchFilters(min_score=5)
        clauses, params = backend._build_filter_clause(filters)

        assert any("min_score" in clause for clause in clauses)
        assert params["min_score"] == 5

    def test_build_filter_clause_with_has_comments_true(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Should filter for ideas with comments."""
        filters = SearchFilters(has_comments=True)
        clauses, params = backend._build_filter_clause(filters)

        assert any("comments" in clause and "> 0" in clause for clause in clauses)

    def test_build_filter_clause_with_has_comments_false(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Should filter for ideas without comments."""
        filters = SearchFilters(has_comments=False)
        clauses, params = backend._build_filter_clause(filters)

        assert any("comments" in clause and "= 0" in clause for clause in clauses)


class TestGetOrderClause:
    """Test ORDER BY clause generation."""

    @pytest.fixture
    def backend(self) -> SQLiteFTS5Backend:
        """Create backend instance."""
        return SQLiteFTS5Backend()

    def test_order_by_relevance(self, backend: SQLiteFTS5Backend) -> None:
        """Relevance sort should use bm25."""
        order = backend._get_order_clause(SearchSortOrder.RELEVANCE)
        assert "bm25" in order

    def test_order_by_date_desc(self, backend: SQLiteFTS5Backend) -> None:
        """Date descending sort should order by created_at DESC."""
        order = backend._get_order_clause(SearchSortOrder.DATE_DESC)
        assert "created_at DESC" in order

    def test_order_by_date_asc(self, backend: SQLiteFTS5Backend) -> None:
        """Date ascending sort should order by created_at ASC."""
        order = backend._get_order_clause(SearchSortOrder.DATE_ASC)
        assert "created_at ASC" in order

    def test_order_by_score_desc(self, backend: SQLiteFTS5Backend) -> None:
        """Score descending sort should compute votes difference."""
        order = backend._get_order_clause(SearchSortOrder.SCORE_DESC)
        assert "UPVOTE" in order
        assert "DOWNVOTE" in order
        assert "DESC" in order

    def test_order_by_score_asc(self, backend: SQLiteFTS5Backend) -> None:
        """Score ascending sort should compute votes difference."""
        order = backend._get_order_clause(SearchSortOrder.SCORE_ASC)
        assert "UPVOTE" in order
        assert "DOWNVOTE" in order
        assert "ASC" in order


class TestCalculateTunedRelevance:
    """Test relevance tuning calculations (Phase 3)."""

    @pytest.fixture
    def backend(self) -> SQLiteFTS5Backend:
        """Create backend instance."""
        return SQLiteFTS5Backend()

    def test_relevance_stays_in_range(self, backend: SQLiteFTS5Backend) -> None:
        """Final relevance should be capped at 1.0."""
        mock_idea = Mock()
        mock_idea.created_at = datetime.now(timezone.utc)
        mock_idea.score = 100  # High score

        result = backend._calculate_tuned_relevance(mock_idea, 0.9)

        assert result <= 1.0

    def test_freshness_boost_for_new_idea(self, backend: SQLiteFTS5Backend) -> None:
        """New ideas should get freshness boost."""
        mock_idea = Mock()
        mock_idea.created_at = datetime.now(timezone.utc)
        mock_idea.score = 0

        result = backend._calculate_tuned_relevance(mock_idea, 0.5)

        # Should be higher than base due to freshness
        assert result >= 0.5

    def test_popularity_boost_for_high_score(self, backend: SQLiteFTS5Backend) -> None:
        """Ideas with high scores should get popularity boost."""
        from datetime import timedelta

        # Old idea to minimize freshness boost
        mock_idea = Mock()
        mock_idea.created_at = datetime.now(timezone.utc) - timedelta(days=400)
        mock_idea.score = 50

        result = backend._calculate_tuned_relevance(mock_idea, 0.5)

        # Should have some boost from popularity
        assert result >= 0.5


class TestSearchIdeasEmptyResults:
    """Test search with empty results scenarios."""

    @pytest.fixture
    def backend(self) -> SQLiteFTS5Backend:
        """Create backend instance."""
        return SQLiteFTS5Backend()

    def test_search_empty_fts_query_returns_empty_results(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Query that produces empty FTS query should return empty results."""
        mock_db = Mock()
        # Use a valid length query but only very short words that get filtered
        query = SearchQuery(q="a b", filters=SearchFilters())

        # Words shorter than 2 chars are filtered, resulting in empty FTS query
        result = backend.search_ideas(mock_db, query)

        assert result.total == 0
        assert result.results == []
        assert result.search_backend == "sqlite_fts5"


class TestGetSuggestions:
    """Test suggestion retrieval."""

    @pytest.fixture
    def backend(self) -> SQLiteFTS5Backend:
        """Create backend instance."""
        return SQLiteFTS5Backend()

    def test_get_suggestions_empty_query(self, backend: SQLiteFTS5Backend) -> None:
        """Empty query should return empty list."""
        mock_db = Mock()
        result = backend.get_suggestions(mock_db, "", limit=5)
        assert result == []

    def test_get_suggestions_whitespace_query(self, backend: SQLiteFTS5Backend) -> None:
        """Whitespace-only query should return empty list."""
        mock_db = Mock()
        result = backend.get_suggestions(mock_db, "   ", limit=5)
        assert result == []

    def test_get_suggestions_returns_titles(self, backend: SQLiteFTS5Backend) -> None:
        """Should return matching titles from FTS."""
        mock_db = Mock()
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("Solar Panel Initiative",),
            ("Solar Energy Project",),
        ]
        mock_db.execute.return_value = mock_result

        result = backend.get_suggestions(mock_db, "solar", limit=5)

        assert len(result) == 2
        assert "Solar Panel Initiative" in result
        assert "Solar Energy Project" in result

    def test_get_suggestions_handles_exception(
        self, backend: SQLiteFTS5Backend
    ) -> None:
        """Should return empty list on database error."""
        mock_db = Mock()
        mock_db.execute.side_effect = Exception("Database error")

        result = backend.get_suggestions(mock_db, "solar", limit=5)

        assert result == []
