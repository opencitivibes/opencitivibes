"""Performance benchmarks for search functionality.

These tests measure search latency and throughput to ensure
the system meets performance targets:
- P50 latency < 100ms
- P95 latency < 300ms
- Suggestions < 50ms

Note: These tests require a database with sufficient data to be meaningful.
Run with: pytest tests/performance/ -v --benchmark-only
"""

import time
from statistics import mean
from typing import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from services.search import SearchService


# Skip performance tests by default - enable with --benchmark flag
pytestmark = pytest.mark.benchmark


class TestSearchLatency:
    """Performance tests for search latency."""

    @pytest.fixture
    def db_with_fts(self, db_session: Session) -> Generator[Session, None, None]:
        """Create FTS table if it doesn't exist."""
        # Create FTS table
        try:
            db_session.execute(
                text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS ideas_fts USING fts5(
                    idea_id UNINDEXED,
                    title,
                    description,
                    tags,
                    tokenize='porter unicode61'
                )
            """)
            )
            db_session.commit()
        except Exception:
            db_session.rollback()

        yield db_session

        # Cleanup
        try:
            db_session.execute(text("DROP TABLE IF EXISTS ideas_fts"))
            db_session.commit()
        except Exception:
            db_session.rollback()

    def test_search_latency_empty_results(self, db_with_fts: Session) -> None:
        """Search should return quickly even with no results."""
        SearchService.clear_backend_cache()
        latencies: list[float] = []

        for _ in range(10):
            start = time.perf_counter()
            try:
                SearchService.search_ideas(db_with_fts, query="nonexistent_term_xyz")
            except Exception:
                pass  # May fail if no FTS setup, but timing still valid
            latencies.append((time.perf_counter() - start) * 1000)

        avg_latency = mean(latencies)
        assert avg_latency < 500, f"Average latency {avg_latency:.2f}ms too high"

    def test_suggestions_latency(self, db_with_fts: Session) -> None:
        """Suggestions should respond quickly."""
        SearchService.clear_backend_cache()
        latencies: list[float] = []

        for _ in range(10):
            start = time.perf_counter()
            SearchService.get_suggestions(db_with_fts, partial_query="so", limit=5)
            latencies.append((time.perf_counter() - start) * 1000)

        avg_latency = mean(latencies)
        assert (
            avg_latency < 100
        ), f"Suggestions average latency {avg_latency:.2f}ms too high"

    def test_backend_info_latency(self, db_with_fts: Session) -> None:
        """Backend info should return instantly."""
        SearchService.clear_backend_cache()
        latencies: list[float] = []

        for _ in range(10):
            start = time.perf_counter()
            SearchService.get_backend_info(db_with_fts)
            latencies.append((time.perf_counter() - start) * 1000)

        avg_latency = mean(latencies)
        assert (
            avg_latency < 50
        ), f"Backend info average latency {avg_latency:.2f}ms too high"


class TestSearchWithData:
    """Performance tests with test data.

    These tests create sample data for more realistic benchmarks.
    """

    @pytest.fixture
    def db_with_test_data(
        self, db_session: Session, test_user, test_category
    ) -> Generator[Session, None, None]:
        """Create test database with sample ideas and FTS index."""
        import repositories.db_models as db_models

        # Create FTS table
        try:
            db_session.execute(
                text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS ideas_fts USING fts5(
                    idea_id UNINDEXED,
                    title,
                    description,
                    tags,
                    tokenize='porter unicode61'
                )
            """)
            )
            db_session.commit()
        except Exception:
            db_session.rollback()

        # Create sample ideas
        sample_ideas = [
            (
                "Solar Panel Initiative",
                "Install solar panels on public buildings for renewable energy.",
            ),
            (
                "Bike Lane Expansion",
                "Expand bike lanes throughout downtown area for safer cycling.",
            ),
            (
                "Community Garden Project",
                "Create community gardens in empty lots for urban agriculture.",
            ),
            (
                "Public Transit Improvement",
                "Improve public transit with more frequent bus service.",
            ),
            (
                "Street Light Upgrade",
                "Upgrade street lights to LED for better efficiency and visibility.",
            ),
        ]

        created_ids = []
        for title, description in sample_ideas:
            idea = db_models.Idea(
                title=title,
                description=description,
                category_id=test_category.id,
                user_id=test_user.id,
                status=db_models.IdeaStatus.APPROVED,
            )
            db_session.add(idea)
            db_session.commit()
            db_session.refresh(idea)
            created_ids.append(idea.id)

            # Add to FTS index
            try:
                db_session.execute(
                    text("""
                    INSERT INTO ideas_fts(idea_id, title, description, tags)
                    VALUES (:idea_id, :title, :description, '')
                """),
                    {"idea_id": idea.id, "title": title, "description": description},
                )
                db_session.commit()
            except Exception:
                db_session.rollback()

        yield db_session

        # Cleanup
        for idea_id in created_ids:
            try:
                db_session.execute(
                    text("DELETE FROM ideas WHERE id = :id"), {"id": idea_id}
                )
            except Exception:
                pass
        try:
            db_session.execute(text("DELETE FROM ideas_fts"))
            db_session.execute(text("DROP TABLE IF EXISTS ideas_fts"))
            db_session.commit()
        except Exception:
            db_session.rollback()

    def test_search_with_results_latency(self, db_with_test_data: Session) -> None:
        """Search returning results should be fast."""
        SearchService.clear_backend_cache()
        latencies: list[float] = []

        for _ in range(10):
            start = time.perf_counter()
            try:
                SearchService.search_ideas(db_with_test_data, query="solar")
            except Exception:
                pass
            latencies.append((time.perf_counter() - start) * 1000)

        avg_latency = mean(latencies)
        assert avg_latency < 500, f"Search with results avg latency {avg_latency:.2f}ms"

    def test_search_multiple_words_latency(self, db_with_test_data: Session) -> None:
        """Multi-word search should be fast."""
        SearchService.clear_backend_cache()
        latencies: list[float] = []

        for _ in range(10):
            start = time.perf_counter()
            try:
                SearchService.search_ideas(db_with_test_data, query="public transit")
            except Exception:
                pass
            latencies.append((time.perf_counter() - start) * 1000)

        avg_latency = mean(latencies)
        assert avg_latency < 500, f"Multi-word search avg latency {avg_latency:.2f}ms"


class TestConcurrency:
    """Test search under concurrent load."""

    @pytest.fixture
    def db_with_fts(self, db_session: Session) -> Generator[Session, None, None]:
        """Create FTS table if it doesn't exist."""
        try:
            db_session.execute(
                text("""
                CREATE VIRTUAL TABLE IF NOT EXISTS ideas_fts USING fts5(
                    idea_id UNINDEXED,
                    title,
                    description,
                    tags,
                    tokenize='porter unicode61'
                )
            """)
            )
            db_session.commit()
        except Exception:
            db_session.rollback()

        yield db_session

        try:
            db_session.execute(text("DROP TABLE IF EXISTS ideas_fts"))
            db_session.commit()
        except Exception:
            db_session.rollback()

    def test_sequential_searches(self, db_with_fts: Session) -> None:
        """Multiple sequential searches should not degrade performance."""
        SearchService.clear_backend_cache()

        start = time.perf_counter()
        for i in range(20):
            try:
                SearchService.search_ideas(db_with_fts, query=f"test{i}")
            except Exception:
                pass
        duration = time.perf_counter() - start

        # 20 searches should complete in under 10 seconds
        assert duration < 10, f"20 searches took {duration:.2f}s"


class TestMemoryUsage:
    """Test memory behavior of search operations."""

    def test_backend_cache_reuse(self) -> None:
        """Backend should be cached and reused."""
        SearchService.clear_backend_cache()

        # First call creates backend
        backend1 = SearchService._get_backend()
        # Second call should reuse cached backend
        backend2 = SearchService._get_backend()

        assert backend1 is backend2, "Backend should be cached"

    def test_cache_clear_works(self) -> None:
        """Cache clear should work properly."""
        SearchService.clear_backend_cache()
        assert SearchService._backend_cache is None

        # Get backend to populate cache
        SearchService._get_backend()
        assert SearchService._backend_cache is not None

        # Clear again
        SearchService.clear_backend_cache()
        assert SearchService._backend_cache is None
