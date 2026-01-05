"""SQLite FTS5 search backend implementation."""

import html
import re
from typing import TYPE_CHECKING, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.search_schemas import (
    SearchFilters,
    SearchHighlight,
    SearchQuery,
    SearchResultItem,
    SearchResults,
    SearchSortOrder,
)
from repositories.idea_repository import IdeaRepository

from .base_backend import SearchBackend

if TYPE_CHECKING:
    pass


class SQLiteFTS5Backend(SearchBackend):
    """SQLite FTS5 full-text search implementation."""

    FTS_TABLE_NAME = "ideas_fts"

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "sqlite_fts5"

    def search_ideas(
        self,
        db: Session,
        query: SearchQuery,
    ) -> SearchResults:
        """Execute FTS5 search on ideas."""
        # Build FTS5 match query
        fts_query = self._build_fts_query(query.q)

        if not fts_query:
            return SearchResults(
                query=query.q,
                total=0,
                results=[],
                filters_applied=query.filters,
                search_backend=self.backend_name,
            )

        # Get matching idea IDs with relevance scores
        fts_results = self._execute_fts_search(
            db, fts_query, query.filters, query.sort, query.skip, query.limit
        )

        if not fts_results:
            return SearchResults(
                query=query.q,
                total=0,
                results=[],
                filters_applied=query.filters,
                search_backend=self.backend_name,
            )

        # Get total count
        total = self._get_total_count(db, fts_query, query.filters)

        # Fetch full idea data with scores
        idea_ids = [r["idea_id"] for r in fts_results]
        idea_repo = IdeaRepository(db)
        ideas = idea_repo.get_ideas_by_ids_with_scores(idea_ids, query.current_user_id)

        # Build result items with highlights
        results = []
        ideas_by_id = {idea.id: idea for idea in ideas}

        # Normalize relevance scores to 0-1 range
        max_relevance = max((r["relevance"] for r in fts_results), default=1.0)
        if max_relevance == 0:
            max_relevance = 1.0

        for fts_result in fts_results:
            idea_id = fts_result["idea_id"]
            if idea_id not in ideas_by_id:
                continue

            idea = ideas_by_id[idea_id]

            # Normalize relevance to 0-1 range
            base_relevance = fts_result["relevance"] / max_relevance

            # Apply relevance tuning (Phase 3)
            final_relevance = self._calculate_tuned_relevance(idea, base_relevance)

            # Generate highlights if requested
            highlights = None
            if query.highlight:
                highlights = self._generate_highlights(
                    query.q, idea.title, idea.description
                )

            results.append(
                SearchResultItem(
                    idea=idea,
                    relevance_score=round(final_relevance, 4),
                    highlights=highlights,
                )
            )

        return SearchResults(
            query=query.q,
            total=total,
            results=results,
            filters_applied=query.filters,
            search_backend=self.backend_name,
        )

    def get_suggestions(
        self,
        db: Session,
        partial_query: str,
        limit: int = 5,
    ) -> list[str]:
        """Get autocomplete suggestions from FTS index."""
        # Use prefix search for suggestions
        words = partial_query.strip().split()
        if not words:
            return []

        # Build prefix query
        fts_query = " ".join(f"{word}*" for word in words)

        sql = text(f"""
            SELECT DISTINCT title
            FROM {self.FTS_TABLE_NAME}
            WHERE {self.FTS_TABLE_NAME} MATCH :query
            LIMIT :limit
        """)  # nosec B608 - FTS_TABLE_NAME is a class constant, not user input

        try:
            result = db.execute(sql, {"query": fts_query, "limit": limit})
            return [row[0] for row in result.fetchall()]
        except Exception:
            return []

    def reindex_idea(
        self,
        db: Session,
        idea_id: int,
    ) -> None:
        """Reindex a single idea."""
        # Import here to avoid circular imports
        import repositories.db_models as db_models

        # Delete existing entry
        db.execute(
            text(f"DELETE FROM {self.FTS_TABLE_NAME} WHERE idea_id = :idea_id"),  # nosec B608 - FTS_TABLE_NAME is a class constant
            {"idea_id": idea_id},
        )

        # Get idea with tags
        idea = db.query(db_models.Idea).filter(db_models.Idea.id == idea_id).first()

        if idea:
            tags_text = " ".join(tag.name for tag in idea.tags)
            db.execute(
                text(f"""
                    INSERT INTO {self.FTS_TABLE_NAME}(idea_id, title, description, tags)
                    VALUES (:idea_id, :title, :description, :tags)
                """),  # nosec B608 - FTS_TABLE_NAME is a class constant, not user input
                {
                    "idea_id": idea.id,
                    "title": idea.title,
                    "description": idea.description or "",
                    "tags": tags_text,
                },
            )

        db.commit()

    def rebuild_index(
        self,
        db: Session,
    ) -> int:
        """Rebuild the entire FTS index."""
        import logging

        # Import here to avoid circular imports
        import repositories.db_models as db_models

        # Clear existing index
        try:
            db.execute(text(f"DELETE FROM {self.FTS_TABLE_NAME}"))  # nosec B608 - FTS_TABLE_NAME is a class constant
        except Exception as e:
            # Log error if FTS table doesn't exist - non-critical for fallback flow
            logging.debug(f"Could not clear FTS index (table may not exist): {e}")

        # Get all ideas with tags
        ideas = db.query(db_models.Idea).all()

        count = 0
        for idea in ideas:
            tags_text = " ".join(tag.name for tag in idea.tags)
            try:
                db.execute(
                    text(f"""
                        INSERT INTO {self.FTS_TABLE_NAME}(idea_id, title, description, tags)
                        VALUES (:idea_id, :title, :description, :tags)
                    """),  # nosec B608 - FTS_TABLE_NAME is a class constant, not user input
                    {
                        "idea_id": idea.id,
                        "title": idea.title,
                        "description": idea.description or "",
                        "tags": tags_text,
                    },
                )
                count += 1
            except Exception as e:
                # Log error but continue with other ideas
                logging.warning(f"Could not reindex idea {idea.id}: {e}")

        db.commit()
        return count

    def is_available(self, db: Session) -> bool:
        """Check if FTS5 table exists and is functional."""
        try:
            result = db.execute(
                text(f"""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='{self.FTS_TABLE_NAME}'
            """)  # nosec B608 - FTS_TABLE_NAME is a class constant, not user input
            )
            if result.fetchone() is None:
                return False

            # Verify the table is functional by running a simple query
            db.execute(text(f"SELECT COUNT(*) FROM {self.FTS_TABLE_NAME}"))  # nosec B608
            return True
        except Exception:
            return False

    def ensure_table_exists(self, db: Session) -> bool:
        """Ensure FTS5 table exists and is functional, recreating if corrupted."""
        import logging

        logger = logging.getLogger(__name__)

        try:
            # Check if table exists and is functional
            if self.is_available(db):
                return True

            logger.warning("FTS5 table missing or corrupted, recreating...")

            # Drop corrupted table if it exists
            try:
                db.execute(
                    text(f"DROP TABLE IF EXISTS {self.FTS_TABLE_NAME}")  # nosec B608
                )
                db.commit()
            except Exception as e:
                logger.debug(f"Could not drop FTS table: {e}")
                db.rollback()

            # Create FTS5 table
            db.execute(
                text(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS {self.FTS_TABLE_NAME}
                    USING fts5(idea_id, title, description, tags)
                """)  # nosec B608 - FTS_TABLE_NAME is a class constant
            )
            db.commit()

            logger.info("FTS5 table created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create FTS5 table: {e}")
            db.rollback()
            return False

    def get_index_stats(self, db: Session) -> dict:
        """Get statistics about the search index."""
        try:
            if not self.is_available(db):
                return {"available": False, "indexed_count": 0, "total_ideas": 0}

            fts_count = (
                db.execute(text(f"SELECT COUNT(*) FROM {self.FTS_TABLE_NAME}")).scalar()  # nosec B608
                or 0
            )
            idea_count = (
                db.execute(
                    text("SELECT COUNT(*) FROM ideas WHERE deleted_at IS NULL")
                ).scalar()
                or 0
            )

            coverage = (fts_count / idea_count * 100) if idea_count > 0 else 100

            return {
                "available": True,
                "indexed_count": fts_count,
                "total_ideas": idea_count,
                "coverage_percent": round(coverage, 1),
            }
        except Exception:
            return {"available": False, "indexed_count": 0, "total_ideas": 0}

    def _build_fts_query(self, query: str) -> str:
        """Build FTS5 match query from user input."""
        # Split into words
        words = query.strip().split()
        if not words:
            return ""

        # Add prefix matching for last word (autocomplete feel)
        # Use OR between words for broader matching
        terms = []
        for i, word in enumerate(words):
            if len(word) < 2:
                continue
            if i == len(words) - 1:
                terms.append(f"{word}*")  # Prefix match on last word
            else:
                terms.append(word)

        if not terms:
            return ""

        return " OR ".join(terms)

    def _build_filter_clause(
        self,
        filters: SearchFilters,
    ) -> tuple[list[str], dict]:
        """Build WHERE clauses and params for filters."""
        where_clauses = ["i.status = :status"]
        params: dict = {"status": filters.status or "APPROVED"}

        # Single category filter
        if filters.category_id:
            where_clauses.append("i.category_id = :category_id")
            params["category_id"] = filters.category_id

        # Multiple categories filter (Phase 3)
        if filters.category_ids:
            placeholders = ", ".join(
                f":cat_{i}" for i in range(len(filters.category_ids))
            )
            where_clauses.append(f"i.category_id IN ({placeholders})")
            for i, cat_id in enumerate(filters.category_ids):
                params[f"cat_{i}"] = cat_id

        if filters.author_id:
            where_clauses.append("i.user_id = :author_id")
            params["author_id"] = filters.author_id

        if filters.from_date:
            where_clauses.append("i.created_at >= :from_date")
            params["from_date"] = filters.from_date

        if filters.to_date:
            where_clauses.append("i.created_at <= :to_date")
            params["to_date"] = filters.to_date

        # Exclude specific IDs (Phase 3)
        if filters.exclude_ids:
            placeholders = ", ".join(
                f":excl_{i}" for i in range(len(filters.exclude_ids))
            )
            where_clauses.append(f"i.id NOT IN ({placeholders})")
            for i, idea_id in enumerate(filters.exclude_ids):
                params[f"excl_{i}"] = idea_id

        # Minimum score filter (Phase 3)
        if filters.min_score is not None:
            where_clauses.append("""(
                (SELECT COUNT(*) FROM votes v WHERE v.idea_id = i.id AND v.vote_type = 'UPVOTE') -
                (SELECT COUNT(*) FROM votes v WHERE v.idea_id = i.id AND v.vote_type = 'DOWNVOTE')
            ) >= :min_score""")
            params["min_score"] = filters.min_score

        # Has comments filter (Phase 3)
        if filters.has_comments is True:
            where_clauses.append(
                "(SELECT COUNT(*) FROM comments c WHERE c.idea_id = i.id) > 0"
            )
        elif filters.has_comments is False:
            where_clauses.append(
                "(SELECT COUNT(*) FROM comments c WHERE c.idea_id = i.id) = 0"
            )

        return where_clauses, params

    def _execute_fts_search(
        self,
        db: Session,
        fts_query: str,
        filters: SearchFilters,
        sort: SearchSortOrder,
        skip: int,
        limit: int,
    ) -> list[dict]:
        """Execute FTS search with filters."""
        # Build WHERE clause for filters
        where_clauses, params = self._build_filter_clause(filters)
        params["query"] = fts_query
        params["skip"] = skip
        params["limit"] = limit

        # Handle tag filtering (Phase 3)
        tag_names = filters.tag_names or filters.tags
        join_sql = ""
        group_by = ""
        if tag_names:
            join_sql = """
                JOIN idea_tags it ON i.id = it.idea_id
                JOIN tags t ON it.tag_id = t.id
            """
            placeholders = ", ".join(f":tag_{i}" for i in range(len(tag_names)))
            where_clauses.append(f"t.name IN ({placeholders})")
            for i, tag in enumerate(tag_names):
                params[f"tag_{i}"] = tag.lower()
            group_by = "GROUP BY fts.idea_id"

        where_sql = " AND ".join(where_clauses)

        # Build ORDER BY clause
        order_sql = self._get_order_clause(sort)

        sql = text(f"""
            SELECT
                fts.idea_id,
                ABS(bm25({self.FTS_TABLE_NAME})) as relevance
            FROM {self.FTS_TABLE_NAME} fts
            JOIN ideas i ON fts.idea_id = i.id
            {join_sql}
            WHERE {self.FTS_TABLE_NAME} MATCH :query
            AND {where_sql}
            {group_by}
            ORDER BY {order_sql}
            LIMIT :limit OFFSET :skip
        """)  # nosec B608 - FTS_TABLE_NAME is a class constant; other vars are built from validated filters

        try:
            result = db.execute(sql, params)
            return [
                {"idea_id": row[0], "relevance": float(row[1])}
                for row in result.fetchall()
            ]
        except Exception:
            return []

    def _get_total_count(
        self,
        db: Session,
        fts_query: str,
        filters: SearchFilters,
    ) -> int:
        """Get total count of matching ideas."""
        where_clauses, params = self._build_filter_clause(filters)
        params["query"] = fts_query

        # Handle tag filtering (Phase 3)
        tag_names = filters.tag_names or filters.tags
        join_sql = ""
        count_expr = "COUNT(*)"
        if tag_names:
            join_sql = """
                JOIN idea_tags it ON i.id = it.idea_id
                JOIN tags t ON it.tag_id = t.id
            """
            placeholders = ", ".join(f":tag_{i}" for i in range(len(tag_names)))
            where_clauses.append(f"t.name IN ({placeholders})")
            for i, tag in enumerate(tag_names):
                params[f"tag_{i}"] = tag.lower()
            count_expr = "COUNT(DISTINCT fts.idea_id)"

        where_sql = " AND ".join(where_clauses)

        sql = text(f"""
            SELECT {count_expr}
            FROM {self.FTS_TABLE_NAME} fts
            JOIN ideas i ON fts.idea_id = i.id
            {join_sql}
            WHERE {self.FTS_TABLE_NAME} MATCH :query
            AND {where_sql}
        """)  # nosec B608 - FTS_TABLE_NAME is a class constant; other vars are built from validated filters

        try:
            result = db.execute(sql, params)
            return result.scalar() or 0
        except Exception:
            return 0

    def _get_order_clause(self, sort: SearchSortOrder) -> str:
        """Get SQL ORDER BY clause for sort order."""
        if sort == SearchSortOrder.RELEVANCE:
            return f"bm25({self.FTS_TABLE_NAME})"  # nosec B608 - FTS_TABLE_NAME is a class constant
        elif sort == SearchSortOrder.DATE_DESC:
            return "i.created_at DESC"
        elif sort == SearchSortOrder.DATE_ASC:
            return "i.created_at ASC"
        elif sort == SearchSortOrder.SCORE_DESC:
            return """(
                SELECT COUNT(*) FROM votes v
                WHERE v.idea_id = i.id AND v.vote_type = 'UPVOTE'
            ) - (
                SELECT COUNT(*) FROM votes v
                WHERE v.idea_id = i.id AND v.vote_type = 'DOWNVOTE'
            ) DESC"""
        elif sort == SearchSortOrder.SCORE_ASC:
            return """(
                SELECT COUNT(*) FROM votes v
                WHERE v.idea_id = i.id AND v.vote_type = 'UPVOTE'
            ) - (
                SELECT COUNT(*) FROM votes v
                WHERE v.idea_id = i.id AND v.vote_type = 'DOWNVOTE'
            ) ASC"""
        return f"bm25({self.FTS_TABLE_NAME})"  # nosec B608 - FTS_TABLE_NAME is a class constant

    def _calculate_tuned_relevance(
        self,
        idea: object,
        base_relevance: float,
    ) -> float:
        """
        Apply relevance tuning based on freshness and popularity (Phase 3).

        Args:
            idea: The idea with score data (IdeaWithScore schema)
            base_relevance: Normalized relevance score (0-1)

        Returns:
            Final relevance score with boosts applied
        """
        from datetime import datetime, timezone

        from models.config import get_settings

        settings = get_settings()

        # Calculate freshness boost (newer ideas get higher boost)
        idea_created = getattr(idea, "created_at", None)
        if idea_created is None:
            # No created_at, skip freshness boost
            freshness = 0.0
        else:
            if idea_created.tzinfo is None:
                idea_created = idea_created.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            age_days = (now - idea_created).days
            freshness = max(0, 1 - (age_days / 365)) * settings.SEARCH_FRESHNESS_BOOST

        # Calculate popularity boost (based on net vote score)
        vote_score = getattr(idea, "score", 0)
        popularity = min(
            vote_score * settings.SEARCH_POPULARITY_BOOST,
            settings.SEARCH_MAX_POPULARITY_BOOST,
        )

        # Combine: base relevance + freshness + popularity
        # Keep final score in 0-1 range
        final = min(1.0, base_relevance + freshness + max(0, popularity))
        return final

    def _generate_highlights(
        self,
        query: str,
        title: str,
        description: Optional[str],
    ) -> SearchHighlight:
        """
        Generate highlighted snippets for search results (Phase 3 enhanced).

        Features:
        - Context-aware snippets centered around matches
        - Multiple highlight snippets for long descriptions
        - Safe HTML escaping to prevent XSS
        """
        words = [w for w in query.lower().split() if len(w) >= 2]

        def strip_html_tags(text_input: str) -> str:
            """Remove HTML tags from text, keeping content."""
            return re.sub(r"<[^>]+>", "", text_input)

        def highlight_text(text_input: str, max_length: int = 500) -> str:
            """Simple highlighting for title."""
            # Strip HTML tags first, then escape remaining special chars
            clean_text = strip_html_tags(text_input)
            safe_text = html.escape(clean_text)
            result = safe_text

            for word in words:
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                result = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", result)

            if len(result) > max_length:
                result = result[:max_length] + "..."

            return result

        def generate_context_snippet(text_input: str, snippet_len: int = 200) -> str:
            """Generate a single context-aware snippet with all matches highlighted."""
            # Strip HTML tags first, then escape
            clean_text = strip_html_tags(text_input)
            safe_text = html.escape(clean_text)

            # Find the first match position to center the snippet
            first_match_pos = len(safe_text)
            for word in words:
                match = re.search(re.escape(word), safe_text, re.IGNORECASE)
                if match and match.start() < first_match_pos:
                    first_match_pos = match.start()

            # Extract a snippet around the first match
            context_before = 60
            context_after = 120
            start = max(0, first_match_pos - context_before)
            end = min(len(safe_text), first_match_pos + context_after)

            snippet = safe_text[start:end]

            # Add ellipsis if truncated
            if start > 0:
                snippet = "..." + snippet
            if end < len(safe_text):
                snippet = snippet + "..."

            # Highlight all matching words in the single snippet
            for word in words:
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                snippet = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", snippet)

            return snippet

        return SearchHighlight(
            title=highlight_text(title, 200) if title else None,
            description=(
                generate_context_snippet(description) if description else None
            ),
        )
