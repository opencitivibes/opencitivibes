"""Search service package."""

from services.search.search_service import SearchService
from services.search.base_backend import SearchBackend
from services.search.sqlite_fts5_backend import SQLiteFTS5Backend
from services.search.postgresql_backend import PostgreSQLFTSBackend

__all__ = [
    "SearchService",
    "SearchBackend",
    "SQLiteFTS5Backend",
    "PostgreSQLFTSBackend",
]
