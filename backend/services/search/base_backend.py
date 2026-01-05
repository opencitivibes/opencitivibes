"""Abstract base class for search backends."""

from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from models.search_schemas import SearchQuery, SearchResults


class SearchBackend(ABC):
    """Abstract interface for search backend implementations."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the name of this backend (e.g., 'sqlite_fts5')."""

    @abstractmethod
    def search_ideas(
        self,
        db: Session,
        query: SearchQuery,
    ) -> SearchResults:
        """
        Execute a full-text search on ideas.

        Args:
            db: Database session
            query: Search query with filters and pagination

        Returns:
            SearchResults with matching ideas and metadata
        """

    @abstractmethod
    def get_suggestions(
        self,
        db: Session,
        partial_query: str,
        limit: int = 5,
    ) -> list[str]:
        """
        Get search suggestions for autocomplete.

        Args:
            db: Database session
            partial_query: Partial search text
            limit: Maximum suggestions to return

        Returns:
            List of suggested search terms
        """

    @abstractmethod
    def reindex_idea(
        self,
        db: Session,
        idea_id: int,
    ) -> None:
        """
        Reindex a single idea after update.

        Args:
            db: Database session
            idea_id: ID of idea to reindex
        """

    @abstractmethod
    def rebuild_index(
        self,
        db: Session,
    ) -> int:
        """
        Rebuild the entire search index.

        Args:
            db: Database session

        Returns:
            Number of ideas indexed
        """

    @abstractmethod
    def is_available(self, db: Session) -> bool:
        """
        Check if this backend is available and properly configured.

        Args:
            db: Database session

        Returns:
            True if backend is ready for use
        """

    def ensure_table_exists(self, db: Session) -> bool:
        """
        Ensure the search backend's storage is ready.

        Optional method - backends that need initialization should override.

        Args:
            db: Database session

        Returns:
            True if storage is ready
        """
        return self.is_available(db)

    def get_index_stats(self, db: Session) -> dict:
        """
        Get statistics about the search index.

        Optional method - backends can override for detailed stats.

        Args:
            db: Database session

        Returns:
            Dict with index statistics
        """
        return {
            "available": self.is_available(db),
            "indexed_count": 0,
            "total_ideas": 0,
            "coverage_percent": 100 if self.is_available(db) else 0,
        }
