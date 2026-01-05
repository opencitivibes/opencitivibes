"""PostgreSQL FTS (Full-Text Search) backend implementation."""

import html
import re
from typing import Any, Optional

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


class PostgreSQLFTSBackend(SearchBackend):
    """PostgreSQL full-text search implementation using tsvector/tsquery."""

    @property
    def backend_name(self) -> str:
        """Return backend identifier."""
        return "postgresql_fts"

    def search_ideas(
        self,
        db: Session,
        query: SearchQuery,
    ) -> SearchResults:
        """Execute PostgreSQL FTS search on ideas."""
        if not query.q.strip():
            return SearchResults(
                query=query.q,
                total=0,
                results=[],
                filters_applied=query.filters,
                search_backend=self.backend_name,
            )

        # Get matching idea IDs with relevance scores
        fts_results = self._execute_fts_search(
            db, query.q, query.filters, query.sort, query.skip, query.limit
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
        total = self._get_total_count(db, query.q, query.filters)

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
                    db, query.q, idea.title, idea.description, query.filters.language
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
        """Get autocomplete suggestions using prefix matching."""
        words = partial_query.strip().split()
        if not words:
            return []

        # Build prefix query for PostgreSQL (word:* syntax)
        prefix_terms = " & ".join(f"{word}:*" for word in words if len(word) >= 2)
        if not prefix_terms:
            return []

        # Use to_tsquery for prefix matching
        sql = text("""
            SELECT DISTINCT title
            FROM ideas
            WHERE (search_vector_en @@ to_tsquery('english', :query)
                   OR search_vector_fr @@ to_tsquery('french', :query))
            AND status = 'APPROVED'
            LIMIT :limit
        """)

        try:
            result = db.execute(sql, {"query": prefix_terms, "limit": limit})
            return [row[0] for row in result.fetchall()]
        except Exception:
            return []

    def reindex_idea(
        self,
        db: Session,
        idea_id: int,
    ) -> None:
        """
        Reindex a single idea by directly updating its search vectors.

        This directly computes and updates the search vectors without relying
        on triggers, ensuring the idea's tags are properly included.
        """
        sql = text("""
            UPDATE ideas
            SET search_vector_en = (
                setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(
                    (SELECT STRING_AGG(t.name, ' ')
                     FROM tags t
                     JOIN idea_tags it ON t.id = it.tag_id
                     WHERE it.idea_id = ideas.id), ''
                )), 'C')
            ),
            search_vector_fr = (
                setweight(to_tsvector('french', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('french', COALESCE(description, '')), 'B') ||
                setweight(to_tsvector('french', COALESCE(
                    (SELECT STRING_AGG(t.name, ' ')
                     FROM tags t
                     JOIN idea_tags it ON t.id = it.tag_id
                     WHERE it.idea_id = ideas.id), ''
                )), 'C')
            )
            WHERE id = :idea_id
        """)
        db.execute(sql, {"idea_id": idea_id})
        db.commit()

    def rebuild_index(
        self,
        db: Session,
    ) -> int:
        """
        Rebuild all search vectors.

        This updates all ideas to trigger the search vector update.
        """
        # Get count first
        count_result = db.execute(text("SELECT COUNT(*) FROM ideas"))
        count = count_result.scalar() or 0

        # Update all ideas to trigger the search vector rebuild
        # The trigger function will recalculate search_vector_en and search_vector_fr
        sql = text("""
            UPDATE ideas
            SET search_vector_en = (
                setweight(to_tsvector('english', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('english', COALESCE(description, '')), 'B') ||
                setweight(to_tsvector('english', COALESCE(
                    (SELECT STRING_AGG(t.name, ' ')
                     FROM tags t
                     JOIN idea_tags it ON t.id = it.tag_id
                     WHERE it.idea_id = ideas.id), ''
                )), 'C')
            ),
            search_vector_fr = (
                setweight(to_tsvector('french', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('french', COALESCE(description, '')), 'B') ||
                setweight(to_tsvector('french', COALESCE(
                    (SELECT STRING_AGG(t.name, ' ')
                     FROM tags t
                     JOIN idea_tags it ON t.id = it.tag_id
                     WHERE it.idea_id = ideas.id), ''
                )), 'C')
            )
        """)
        db.execute(sql)
        db.commit()

        return count

    def is_available(self, db: Session) -> bool:
        """Check if PostgreSQL FTS is properly configured."""
        try:
            # Check if the search vector columns exist
            result = db.execute(
                text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'ideas'
                AND column_name IN ('search_vector_en', 'search_vector_fr')
            """)
            )
            columns = [row[0] for row in result.fetchall()]
            return "search_vector_en" in columns and "search_vector_fr" in columns
        except Exception:
            return False

    def _build_filter_clause(
        self,
        filters: SearchFilters,
    ) -> tuple[list[str], dict]:
        """Build WHERE clauses and params for filters."""
        where_clauses = ["ideas.status = :status"]
        params: dict = {"status": filters.status or "APPROVED"}

        # Single category filter
        if filters.category_id:
            where_clauses.append("ideas.category_id = :category_id")
            params["category_id"] = filters.category_id

        # Multiple categories filter (Phase 3)
        if filters.category_ids:
            placeholders = ", ".join(
                f":cat_{i}" for i in range(len(filters.category_ids))
            )
            where_clauses.append(f"ideas.category_id IN ({placeholders})")
            for i, cat_id in enumerate(filters.category_ids):
                params[f"cat_{i}"] = cat_id

        if filters.author_id:
            where_clauses.append("ideas.user_id = :author_id")
            params["author_id"] = filters.author_id

        if filters.from_date:
            where_clauses.append("ideas.created_at >= :from_date")
            params["from_date"] = filters.from_date

        if filters.to_date:
            where_clauses.append("ideas.created_at <= :to_date")
            params["to_date"] = filters.to_date

        # Exclude specific IDs (Phase 3)
        if filters.exclude_ids:
            placeholders = ", ".join(
                f":excl_{i}" for i in range(len(filters.exclude_ids))
            )
            where_clauses.append(f"ideas.id NOT IN ({placeholders})")
            for i, idea_id in enumerate(filters.exclude_ids):
                params[f"excl_{i}"] = idea_id

        # Minimum score filter (Phase 3)
        if filters.min_score is not None:
            where_clauses.append("""(
                (SELECT COUNT(*) FROM votes v WHERE v.idea_id = ideas.id AND v.vote_type = 'UPVOTE') -
                (SELECT COUNT(*) FROM votes v WHERE v.idea_id = ideas.id AND v.vote_type = 'DOWNVOTE')
            ) >= :min_score""")
            params["min_score"] = filters.min_score

        # Has comments filter (Phase 3)
        if filters.has_comments is True:
            where_clauses.append(
                "(SELECT COUNT(*) FROM comments c WHERE c.idea_id = ideas.id) > 0"
            )
        elif filters.has_comments is False:
            where_clauses.append(
                "(SELECT COUNT(*) FROM comments c WHERE c.idea_id = ideas.id) = 0"
            )

        return where_clauses, params

    def _execute_fts_search(
        self,
        db: Session,
        query_text: str,
        filters: SearchFilters,
        sort: SearchSortOrder,
        skip: int,
        limit: int,
    ) -> list[dict]:
        """Execute FTS search with filters."""
        # Build WHERE clause for filters
        where_clauses, params = self._build_filter_clause(filters)
        params["query"] = query_text
        params["skip"] = skip
        params["limit"] = limit

        # Handle tag filtering (Phase 3)
        tag_names = filters.tag_names or filters.tags
        join_sql = ""
        group_by = ""
        if tag_names:
            join_sql = """
                JOIN idea_tags it ON ideas.id = it.idea_id
                JOIN tags t ON it.tag_id = t.id
            """
            placeholders = ", ".join(f":tag_{i}" for i in range(len(tag_names)))
            where_clauses.append(f"t.name IN ({placeholders})")
            for i, tag in enumerate(tag_names):
                params[f"tag_{i}"] = tag.lower()
            group_by = (
                "GROUP BY ideas.id, ideas.search_vector_en, ideas.search_vector_fr"
            )

        where_sql = " AND ".join(where_clauses)

        # Build ORDER BY clause
        order_sql = self._get_order_clause(sort)

        # Determine which vector(s) to search based on language filter
        if filters.language == "en":
            vector_match = (
                "ideas.search_vector_en @@ plainto_tsquery('english', :query)"
            )
            rank_expr = (
                "ts_rank(ideas.search_vector_en, plainto_tsquery('english', :query))"
            )
        elif filters.language == "fr":
            vector_match = "ideas.search_vector_fr @@ plainto_tsquery('french', :query)"
            rank_expr = (
                "ts_rank(ideas.search_vector_fr, plainto_tsquery('french', :query))"
            )
        else:
            # Search both languages
            vector_match = """(
                ideas.search_vector_en @@ plainto_tsquery('english', :query)
                OR ideas.search_vector_fr @@ plainto_tsquery('french', :query)
            )"""
            rank_expr = """GREATEST(
                ts_rank(ideas.search_vector_en, plainto_tsquery('english', :query)),
                ts_rank(ideas.search_vector_fr, plainto_tsquery('french', :query))
            )"""

        sql = text(f"""
            SELECT
                ideas.id as idea_id,
                {rank_expr} as relevance
            FROM ideas
            {join_sql}
            WHERE {vector_match}
            AND {where_sql}
            {group_by}
            ORDER BY {order_sql}
            LIMIT :limit OFFSET :skip
        """)  # nosec B608 - all variables are built from validated filters and internal expressions

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
        query_text: str,
        filters: SearchFilters,
    ) -> int:
        """Get total count of matching ideas."""
        where_clauses, params = self._build_filter_clause(filters)
        params["query"] = query_text

        # Handle tag filtering (Phase 3)
        tag_names = filters.tag_names or filters.tags
        join_sql = ""
        count_expr = "COUNT(*)"
        if tag_names:
            join_sql = """
                JOIN idea_tags it ON ideas.id = it.idea_id
                JOIN tags t ON it.tag_id = t.id
            """
            placeholders = ", ".join(f":tag_{i}" for i in range(len(tag_names)))
            where_clauses.append(f"t.name IN ({placeholders})")
            for i, tag in enumerate(tag_names):
                params[f"tag_{i}"] = tag.lower()
            count_expr = "COUNT(DISTINCT ideas.id)"

        where_sql = " AND ".join(where_clauses)

        # Determine which vector(s) to search
        if filters.language == "en":
            vector_match = (
                "ideas.search_vector_en @@ plainto_tsquery('english', :query)"
            )
        elif filters.language == "fr":
            vector_match = "ideas.search_vector_fr @@ plainto_tsquery('french', :query)"
        else:
            vector_match = """(
                ideas.search_vector_en @@ plainto_tsquery('english', :query)
                OR ideas.search_vector_fr @@ plainto_tsquery('french', :query)
            )"""

        sql = text(f"""
            SELECT {count_expr}
            FROM ideas
            {join_sql}
            WHERE {vector_match}
            AND {where_sql}
        """)  # nosec B608 - all variables are built from validated filters and internal expressions

        try:
            result = db.execute(sql, params)
            return result.scalar() or 0
        except Exception:
            return 0

    def _get_order_clause(self, sort: SearchSortOrder) -> str:
        """Get SQL ORDER BY clause for sort order."""
        if sort == SearchSortOrder.RELEVANCE:
            return "relevance DESC"
        elif sort == SearchSortOrder.DATE_DESC:
            return "created_at DESC"
        elif sort == SearchSortOrder.DATE_ASC:
            return "created_at ASC"
        elif sort == SearchSortOrder.SCORE_DESC:
            return """(
                SELECT COUNT(*) FROM votes v
                WHERE v.idea_id = ideas.id AND v.vote_type = 'UPVOTE'
            ) - (
                SELECT COUNT(*) FROM votes v
                WHERE v.idea_id = ideas.id AND v.vote_type = 'DOWNVOTE'
            ) DESC"""
        elif sort == SearchSortOrder.SCORE_ASC:
            return """(
                SELECT COUNT(*) FROM votes v
                WHERE v.idea_id = ideas.id AND v.vote_type = 'UPVOTE'
            ) - (
                SELECT COUNT(*) FROM votes v
                WHERE v.idea_id = ideas.id AND v.vote_type = 'DOWNVOTE'
            ) ASC"""
        return "relevance DESC"

    def _calculate_tuned_relevance(
        self,
        idea: Any,  # IdeaWithScore - using Any to avoid import cycles
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
        idea_created = idea.created_at
        if idea_created.tzinfo is None:
            idea_created = idea_created.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        age_days = (now - idea_created).days
        freshness = max(0, 1 - (age_days / 365)) * settings.SEARCH_FRESHNESS_BOOST

        # Calculate popularity boost (based on net vote score)
        vote_score = idea.score if hasattr(idea, "score") else 0
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
        db: Session,
        query_text: str,
        title: str,
        description: Optional[str],
        language: Optional[str],
    ) -> SearchHighlight:
        """Generate highlighted snippets using PostgreSQL ts_headline."""
        # Use ts_headline for PostgreSQL native highlighting
        lang_config = (
            "english"
            if language == "en"
            else "french"
            if language == "fr"
            else "english"
        )

        try:
            # Generate title highlight
            title_hl_result = db.execute(
                text("""
                    SELECT ts_headline(
                        :lang_config,
                        :title,
                        plainto_tsquery(:lang_config, :query),
                        'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=10'
                    )
                """),
                {"lang_config": lang_config, "title": title, "query": query_text},
            )
            title_hl = title_hl_result.scalar()

            # Generate description highlight
            desc_hl = None
            if description:
                desc_hl_result = db.execute(
                    text("""
                        SELECT ts_headline(
                            :lang_config,
                            :description,
                            plainto_tsquery(:lang_config, :query),
                            'StartSel=<mark>, StopSel=</mark>, MaxWords=50, MinWords=25'
                        )
                    """),
                    {
                        "lang_config": lang_config,
                        "description": description,
                        "query": query_text,
                    },
                )
                desc_hl = desc_hl_result.scalar()

            return SearchHighlight(
                title=title_hl,
                description=desc_hl,
            )
        except Exception:
            # Fallback to simple highlighting
            return self._generate_highlights_fallback(query_text, title, description)

    def _generate_highlights_fallback(
        self,
        query: str,
        title: str,
        description: Optional[str],
    ) -> SearchHighlight:
        """Fallback highlighting using regex (same as SQLite backend)."""
        words = query.lower().split()

        def highlight_text(text_content: str, max_length: int = 500) -> str:
            # Escape HTML first for security
            safe_text = html.escape(text_content)
            result = safe_text

            for word in words:
                if len(word) < 2:
                    continue
                # Case-insensitive replacement with <mark> tags
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                result = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", result)

            # Truncate if needed
            if len(result) > max_length:
                result = result[:max_length] + "..."

            return result

        return SearchHighlight(
            title=highlight_text(title, 200) if title else None,
            description=highlight_text(description, 500) if description else None,
        )
