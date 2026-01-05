"""Search service - main entry point for search functionality."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy.orm import Session

from models.config import get_settings
from models.exceptions import ValidationException
from models.search_schemas import (
    SearchFilters,
    SearchQuery,
    SearchResults,
    SearchSortOrder,
)

from .base_backend import SearchBackend

if TYPE_CHECKING:
    import models.schemas as schemas


class SearchService:
    """
    Search service providing full-text search across ideas.

    Follows the static method pattern for consistency with other services.
    Automatically selects the appropriate backend based on configuration.
    """

    _backend_cache: Optional[SearchBackend] = None

    @staticmethod
    def _get_backend() -> SearchBackend:
        """Get the configured search backend."""
        if SearchService._backend_cache is not None:
            return SearchService._backend_cache

        settings = get_settings()
        backend_name = settings.get_search_backend()

        if backend_name == "sqlite_fts5":
            from .sqlite_fts5_backend import SQLiteFTS5Backend

            SearchService._backend_cache = SQLiteFTS5Backend()
        elif backend_name == "postgresql_fts":
            from .postgresql_backend import PostgreSQLFTSBackend

            SearchService._backend_cache = PostgreSQLFTSBackend()
        else:
            # Default to SQLite FTS5
            from .sqlite_fts5_backend import SQLiteFTS5Backend

            SearchService._backend_cache = SQLiteFTS5Backend()

        return SearchService._backend_cache

    @staticmethod
    def search_ideas(
        db: Session,
        query: str,
        category_id: Optional[int] = None,
        status: Optional[str] = "APPROVED",
        author_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        language: Optional[str] = None,
        sort: SearchSortOrder = SearchSortOrder.RELEVANCE,
        skip: int = 0,
        limit: int = 20,
        highlight: bool = True,
        current_user_id: Optional[int] = None,
        # Phase 3: Enhanced filters
        category_ids: Optional[list[int]] = None,
        tag_names: Optional[list[str]] = None,
        min_score: Optional[int] = None,
        has_comments: Optional[bool] = None,
        exclude_ids: Optional[list[int]] = None,
        # Phase 3: Language prioritization
        preferred_language: Optional[str] = None,
    ) -> SearchResults:
        """
        Search ideas using full-text search.

        Args:
            db: Database session
            query: Search query string (min 2 characters)
            category_id: Optional category filter
            status: Idea status filter (default: APPROVED)
            author_id: Optional author filter
            from_date: Optional start date filter
            to_date: Optional end date filter
            language: Optional language filter (en/fr) - filters results
            sort: Sort order (default: relevance)
            skip: Pagination offset
            limit: Results per page (max 100)
            highlight: Include highlighted snippets
            current_user_id: Optional current user ID for vote status
            category_ids: Optional multiple category filter (Phase 3)
            tag_names: Optional tag filter (Phase 3)
            min_score: Optional minimum vote score filter (Phase 3)
            has_comments: Optional filter for ideas with/without comments (Phase 3)
            exclude_ids: Optional list of idea IDs to exclude (Phase 3)
            preferred_language: Optional language ('fr'|'en') for prioritization.
                Results are reordered so preferred language appears first while
                preserving relevance order within each language group.

        Returns:
            SearchResults with matching ideas

        Raises:
            ValidationException: If query is too short or invalid
        """
        settings = get_settings()

        # Validate query length
        query = query.strip()
        if len(query) < settings.SEARCH_MIN_QUERY_LENGTH:
            raise ValidationException(
                f"Search query must be at least {settings.SEARCH_MIN_QUERY_LENGTH} characters"
            )

        # Cap limit
        limit = min(limit, settings.SEARCH_MAX_RESULTS)

        # Build search query object with Phase 3 filters
        search_query = SearchQuery(
            q=query,
            filters=SearchFilters(
                category_id=category_id,
                status=status,
                author_id=author_id,
                from_date=from_date,
                to_date=to_date,
                language=language,
                category_ids=category_ids,
                tag_names=tag_names,
                min_score=min_score,
                has_comments=has_comments,
                exclude_ids=exclude_ids,
            ),
            sort=sort,
            skip=skip,
            limit=limit,
            highlight=highlight,
            current_user_id=current_user_id,
        )

        # Execute search
        backend = SearchService._get_backend()

        if not backend.is_available(db):
            # Return empty results if backend not available
            return SearchResults(
                query=query,
                total=0,
                results=[],
                filters_applied=search_query.filters,
                search_backend=backend.backend_name,
            )

        results = backend.search_ideas(db, search_query)

        # Apply language prioritization if requested
        # Reorder results so preferred language appears first, preserving
        # relevance order within each language group
        if preferred_language and results.results:
            lang = preferred_language.lower()
            if lang in ("fr", "en"):
                # Stable sort: preferred language first (0), others second (1)
                # Original order preserved within each group
                results.results = sorted(
                    results.results,
                    key=lambda item: 0 if item.idea.language == lang else 1,
                )

        return results

    @staticmethod
    def get_suggestions(
        db: Session,
        partial_query: str,
        limit: int = 5,
    ) -> list[str]:
        """
        Get search suggestions for autocomplete.

        Args:
            db: Database session
            partial_query: Partial search text
            limit: Maximum suggestions (default: 5)

        Returns:
            List of suggested search terms
        """
        if len(partial_query.strip()) < 2:
            return []

        backend = SearchService._get_backend()

        if not backend.is_available(db):
            return []

        return backend.get_suggestions(db, partial_query, min(limit, 10))

    @staticmethod
    def reindex_idea(db: Session, idea_id: int) -> None:
        """
        Reindex a single idea after update.

        Args:
            db: Database session
            idea_id: ID of idea to reindex
        """
        backend = SearchService._get_backend()
        if backend.is_available(db):
            backend.reindex_idea(db, idea_id)

    @staticmethod
    def rebuild_index(db: Session) -> int:
        """
        Rebuild the entire search index.

        Args:
            db: Database session

        Returns:
            Number of ideas indexed
        """
        backend = SearchService._get_backend()
        if not backend.is_available(db):
            return 0
        return backend.rebuild_index(db)

    @staticmethod
    def get_backend_info(db: Session) -> "schemas.SearchBackendInfo":
        """
        Get information about the current search backend.

        Returns:
            SearchBackendInfo schema with backend name and availability status
        """
        import models.schemas as schemas

        backend = SearchService._get_backend()
        return schemas.SearchBackendInfo(
            backend=backend.backend_name,
            available=backend.is_available(db),
        )

    @staticmethod
    def clear_backend_cache() -> None:
        """Clear the cached backend instance (for testing)."""
        SearchService._backend_cache = None

    @staticmethod
    def ensure_index_ready(db: Session) -> bool:
        """
        Ensure search index is ready, recreating if corrupted.

        Called on startup to verify/repair search functionality.

        Returns:
            True if index is ready, False otherwise
        """
        import logging

        logger = logging.getLogger(__name__)

        backend = SearchService._get_backend()

        # For SQLite FTS5, check and repair table
        if hasattr(backend, "ensure_table_exists"):
            if not backend.ensure_table_exists(db):
                logger.error("Failed to ensure FTS table exists")
                return False

        # Check if index needs rebuilding
        if hasattr(backend, "get_index_stats"):
            stats = backend.get_index_stats(db)
            if stats.get("available"):
                coverage = stats.get("coverage_percent", 100)
                if coverage < 90:
                    logger.warning(
                        f"Search index incomplete ({coverage:.1f}% coverage), rebuilding..."
                    )
                    count = SearchService.rebuild_index(db)
                    logger.info(f"Search index rebuilt: {count} ideas indexed")
                else:
                    logger.info(
                        f"Search index verified: {stats['indexed_count']} ideas indexed"
                    )
            else:
                logger.warning("Search backend not available, rebuilding index...")
                count = SearchService.rebuild_index(db)
                logger.info(f"Search index rebuilt: {count} ideas indexed")

        return backend.is_available(db)

    @staticmethod
    def get_health_status(db: Session) -> "schemas.SearchHealthStatus":
        """
        Get detailed health status of search backend.

        Returns:
            SearchHealthStatus schema with health status and index statistics
        """
        import models.schemas as schemas

        backend = SearchService._get_backend()

        if not backend.is_available(db):
            return schemas.SearchHealthStatus(
                status="unavailable",
                backend=backend.backend_name,
                message="Search backend not available",
            )

        # Get index stats
        if hasattr(backend, "get_index_stats"):
            stats = backend.get_index_stats(db)
            coverage = stats.get("coverage_percent", 0)

            return schemas.SearchHealthStatus(
                status="healthy" if coverage >= 90 else "degraded",
                backend=backend.backend_name,
                indexed_count=stats.get("indexed_count", 0),
                total_ideas=stats.get("total_ideas", 0),
                coverage_percent=coverage,
                message="Index complete" if coverage >= 90 else "Index needs rebuild",
            )

        return schemas.SearchHealthStatus(
            status="healthy",
            backend=backend.backend_name,
            message="Search backend available",
        )

    @staticmethod
    def remove_idea_from_index(db: Session, idea_id: int) -> None:
        """
        Remove an idea from the search index.

        Args:
            db: Database session
            idea_id: ID of idea to remove
        """
        import logging

        from sqlalchemy import text

        logger = logging.getLogger(__name__)

        backend = SearchService._get_backend()
        if not backend.is_available(db):
            return

        try:
            # Use backend's table name constant
            table_name = getattr(backend, "FTS_TABLE_NAME", "ideas_fts")
            db.execute(
                text(f"DELETE FROM {table_name} WHERE idea_id = :idea_id"),  # nosec B608 - table_name is a class constant
                {"idea_id": idea_id},
            )
            db.commit()
        except Exception as e:
            logger.error(f"Failed to remove idea {idea_id} from index: {e}")
            db.rollback()

    @staticmethod
    def search_by_tag(
        db: Session,
        tag_query: str,
        skip: int = 0,
        limit: int = 20,
        current_user_id: Optional[int] = None,
    ) -> SearchResults:
        """
        Search ideas by tag name only (Phase 3).

        This is used when query starts with '#'.

        Args:
            db: Database session
            tag_query: Tag name to search (without '#')
            skip: Pagination offset
            limit: Results per page
            current_user_id: Optional current user ID for vote status

        Returns:
            SearchResults with matching ideas
        """
        from models.search_schemas import SearchResultItem
        from repositories.idea_repository import IdeaRepository
        from repositories.tag_repository import TagRepository

        tag_repo = TagRepository(db)
        tags = tag_repo.search_tags(tag_query, limit=10)

        if not tags:
            backend = SearchService._get_backend()
            return SearchResults(
                query=f"#{tag_query}",
                total=0,
                results=[],
                filters_applied=SearchFilters(status="APPROVED"),
                search_backend=backend.backend_name,
            )

        # Get idea IDs for matching tags
        tag_ids = [t.id for t in tags]
        idea_ids = tag_repo.get_idea_ids_for_tags(tag_ids, skip=skip, limit=limit)

        if not idea_ids:
            backend = SearchService._get_backend()
            return SearchResults(
                query=f"#{tag_query}",
                total=0,
                results=[],
                filters_applied=SearchFilters(status="APPROVED"),
                search_backend=backend.backend_name,
            )

        # Fetch full idea data
        idea_repo = IdeaRepository(db)
        ideas = idea_repo.get_ideas_by_ids_with_scores(idea_ids, current_user_id)

        results = [
            SearchResultItem(
                idea=idea,
                relevance_score=1.0,  # Tag matches are fully relevant
                highlights=None,
            )
            for idea in ideas
        ]

        backend = SearchService._get_backend()
        return SearchResults(
            query=f"#{tag_query}",
            total=len(results),
            results=results,
            filters_applied=SearchFilters(status="APPROVED"),
            search_backend=backend.backend_name,
        )

    @staticmethod
    def search_with_tags(
        db: Session,
        query: str,
        skip: int = 0,
        limit: int = 20,
        current_user_id: Optional[int] = None,
    ) -> dict:
        """
        Search ideas and return matching tags alongside results (Phase 3).

        Args:
            db: Database session
            query: Search query (if starts with '#', searches tags only)
            skip: Pagination offset
            limit: Results per page
            current_user_id: Optional current user ID for vote status

        Returns:
            Dict with 'ideas' (SearchResults) and 'matching_tags' (list)
        """
        from models.search_schemas import TagSuggestion
        from repositories.tag_repository import TagRepository

        # If query starts with #, search tags only
        if query.startswith("#"):
            tag_query = query[1:].strip()
            return {
                "ideas": SearchService.search_by_tag(
                    db, tag_query, skip, limit, current_user_id
                ),
                "matching_tags": [],
            }

        # Otherwise, search both ideas and get matching tags
        idea_results = SearchService.search_ideas(
            db=db,
            query=query,
            skip=skip,
            limit=limit,
            current_user_id=current_user_id,
        )

        # Get matching tags
        tag_repo = TagRepository(db)
        tags = tag_repo.search_tags(query, limit=5)

        matching_tags = [
            TagSuggestion(
                name=tag.name,
                display_name=tag.display_name,
                idea_count=tag_repo.get_tag_idea_count(tag.id),
            )
            for tag in tags
        ]

        return {
            "ideas": idea_results,
            "matching_tags": matching_tags,
        }

    @staticmethod
    def get_autocomplete(
        db: Session,
        query: str,
        limit: int = 5,
    ) -> dict:
        """
        Get combined autocomplete suggestions for ideas and tags (Phase 3).

        Args:
            db: Database session
            query: Partial search text
            limit: Maximum suggestions per type

        Returns:
            Dict with 'ideas' (list[str]), 'tags' (list), and 'queries' (list[str])
        """
        from models.search_schemas import TagSuggestion
        from repositories.tag_repository import TagRepository

        if len(query.strip()) < 2:
            return {"ideas": [], "tags": [], "queries": []}

        # Get idea title suggestions
        backend = SearchService._get_backend()
        idea_suggestions = []
        if backend.is_available(db):
            idea_suggestions = backend.get_suggestions(db, query, limit)

        # Get tag suggestions
        tag_repo = TagRepository(db)
        tags = tag_repo.search_tags(query, limit=limit)

        tag_suggestions = [
            TagSuggestion(
                name=tag.name,
                display_name=tag.display_name,
                idea_count=tag_repo.get_tag_idea_count(tag.id),
            )
            for tag in tags
        ]

        return {
            "ideas": idea_suggestions,
            "tags": tag_suggestions,
            "queries": [],  # Popular queries - optional, implemented in Phase 3.6
        }
