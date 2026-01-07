"""
Idea repository for database operations.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, List, Optional, Union

from sqlalchemy import case, func, literal
from sqlalchemy.orm import Session

import repositories.db_models as db_models
from repositories.vote_quality_repository import VoteQualityRepository

if TYPE_CHECKING:
    import models.schemas as schemas
from .base import BaseRepository


class IdeaRepository(BaseRepository[db_models.Idea]):
    """Repository for Idea entity database operations."""

    def __init__(self, db: Session):
        """
        Initialize idea repository.

        Args:
            db: Database session
        """
        super().__init__(db_models.Idea, db)

    def _fetch_tags_batch(self, idea_ids: list[int]) -> dict[int, list[db_models.Tag]]:
        """Fetch all tags for given idea IDs in a single query."""
        if not idea_ids:
            return {}

        tag_results = (
            self.db.query(db_models.IdeaTag.idea_id, db_models.Tag)
            .join(db_models.Tag, db_models.IdeaTag.tag_id == db_models.Tag.id)
            .filter(db_models.IdeaTag.idea_id.in_(idea_ids))
            .order_by(db_models.IdeaTag.idea_id, db_models.Tag.display_name)
            .all()
        )

        tags_by_idea: dict[int, list[db_models.Tag]] = {}
        for idea_id, tag in tag_results:
            if idea_id not in tags_by_idea:
                tags_by_idea[idea_id] = []
            tags_by_idea[idea_id].append(tag)

        return tags_by_idea

    def get_by_status(
        self, status: db_models.IdeaStatus, skip: int = 0, limit: int = 100
    ) -> List[db_models.Idea]:
        """
        Get ideas by status.

        Args:
            status: Idea status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ideas
        """
        return (
            self.db.query(db_models.Idea)
            .filter(db_models.Idea.status == status)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_category(
        self,
        category_id: int,
        status: Optional[db_models.IdeaStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.Idea]:
        """
        Get ideas by category.

        Args:
            category_id: Category ID
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ideas
        """
        query = self.db.query(db_models.Idea).filter(
            db_models.Idea.category_id == category_id
        )
        if status:
            query = query.filter(db_models.Idea.status == status)
        return query.offset(skip).limit(limit).all()

    def get_by_user(
        self,
        user_id: int,
        status: Optional[db_models.IdeaStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.Idea]:
        """
        Get ideas by user.

        Args:
            user_id: User ID
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ideas
        """
        query = self.db.query(db_models.Idea).filter(db_models.Idea.user_id == user_id)
        if status:
            query = query.filter(db_models.Idea.status == status)
        return query.offset(skip).limit(limit).all()

    def get_ideas_with_scores(
        self,
        status_filter: Union[
            db_models.IdeaStatus, List[db_models.IdeaStatus]
        ] = db_models.IdeaStatus.APPROVED,
        category_id: Optional[int] = None,
        user_id: Optional[int] = None,
        current_user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
        idea_id: Optional[int] = None,
        preferred_language: Optional[str] = None,
    ) -> List["schemas.IdeaWithScore"]:
        """
        Get ideas with vote counts, scores, and user vote information.

        This method builds a complex query with subqueries for:
        - Upvote counts
        - Downvote counts
        - Comment counts (excluding moderated)
        - User's current vote (if authenticated)
        - Calculates score as upvotes - downvotes

        Args:
            status_filter: Filter by idea status
            category_id: Optional category filter
            user_id: Optional user filter (ideas by this user)
            current_user_id: Current authenticated user ID (for user_vote field)
            skip: Number of records to skip
            limit: Maximum number of records to return
            idea_id: Optional specific idea ID to fetch
            preferred_language: Optional language code ('fr' or 'en') for
                prioritization. When set, ideas in the preferred language appear
                first, followed by other languages. All ideas remain visible.

        Returns:
            List of ideas with scores and vote information
        """
        import sentry_sdk

        import models.schemas as schemas

        # Start performance span for database query
        sentry_sdk.set_tag("repo.method", "get_ideas_with_scores")

        # Subquery for upvotes
        upvotes_subq = (
            self.db.query(
                db_models.Vote.idea_id,
                func.count(db_models.Vote.id).label("upvotes"),
            )
            .filter(db_models.Vote.vote_type == db_models.VoteType.UPVOTE)
            .group_by(db_models.Vote.idea_id)
            .subquery()
        )

        # Subquery for downvotes
        downvotes_subq = (
            self.db.query(
                db_models.Vote.idea_id, func.count(db_models.Vote.id).label("downvotes")
            )
            .filter(db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE)
            .group_by(db_models.Vote.idea_id)
            .subquery()
        )

        # Subquery for comment count (only visible comments)
        comments_subq = (
            self.db.query(
                db_models.Comment.idea_id,
                func.count(db_models.Comment.id).label("comment_count"),
            )
            .filter(
                db_models.Comment.is_moderated.is_(False),
                db_models.Comment.deleted_at.is_(None),
                db_models.Comment.is_hidden.is_(False),
                db_models.Comment.requires_approval.is_(False),
            )
            .group_by(db_models.Comment.idea_id)
            .subquery()
        )

        # User vote subquery (if user is authenticated)
        user_vote_subq = None
        if current_user_id:
            user_vote_subq = (
                self.db.query(
                    db_models.Vote.idea_id, db_models.Vote.vote_type.label("user_vote")
                )
                .filter(db_models.Vote.user_id == current_user_id)
                .subquery()
            )

        # Main query
        query = (
            self.db.query(
                db_models.Idea,
                db_models.User.username.label("author_username"),
                db_models.User.display_name.label("author_display_name"),
                db_models.Category.name_en.label("category_name_en"),
                db_models.Category.name_fr.label("category_name_fr"),
                func.coalesce(upvotes_subq.c.upvotes, 0).label("upvotes"),
                func.coalesce(downvotes_subq.c.downvotes, 0).label("downvotes"),
                (
                    func.coalesce(upvotes_subq.c.upvotes, 0)
                    - func.coalesce(downvotes_subq.c.downvotes, 0)
                ).label("score"),
                func.coalesce(comments_subq.c.comment_count, 0).label("comment_count"),
                user_vote_subq.c.user_vote
                if user_vote_subq is not None
                else literal(None).label("user_vote"),
            )
            .join(db_models.User, db_models.Idea.user_id == db_models.User.id)
            .join(
                db_models.Category, db_models.Idea.category_id == db_models.Category.id
            )
            .outerjoin(upvotes_subq, db_models.Idea.id == upvotes_subq.c.idea_id)
            .outerjoin(downvotes_subq, db_models.Idea.id == downvotes_subq.c.idea_id)
            .outerjoin(comments_subq, db_models.Idea.id == comments_subq.c.idea_id)
        )

        if user_vote_subq is not None:
            query = query.outerjoin(
                user_vote_subq, db_models.Idea.id == user_vote_subq.c.idea_id
            )

        # Apply filters - always exclude deleted ideas
        # Handle both single status and list of statuses
        if isinstance(status_filter, list):
            query = query.filter(
                db_models.Idea.status.in_(status_filter),
                db_models.Idea.deleted_at.is_(None),
            )
        else:
            query = query.filter(
                db_models.Idea.status == status_filter,
                db_models.Idea.deleted_at.is_(None),
            )

        if category_id:
            query = query.filter(db_models.Idea.category_id == category_id)

        if user_id:
            query = query.filter(db_models.Idea.user_id == user_id)

        if idea_id:
            query = query.filter(db_models.Idea.id == idea_id)

        # Build ORDER BY clause
        # If preferred_language is set, prioritize that language first
        # (0 for preferred language, 1 for others), then by score, then by date
        order_by_clauses = []

        if preferred_language:
            # Normalize language and add language priority to ordering
            lang = preferred_language.lower()
            if lang in ("fr", "en"):
                language_priority = case(
                    (db_models.Idea.language == lang, 0),
                    else_=1,
                )
                order_by_clauses.append(language_priority)

        # Always order by score descending, then by created_at descending
        score_expr = func.coalesce(upvotes_subq.c.upvotes, 0) - func.coalesce(
            downvotes_subq.c.downvotes, 0
        )
        order_by_clauses.append(score_expr.desc())
        order_by_clauses.append(db_models.Idea.created_at.desc())

        query = query.order_by(*order_by_clauses)

        # Pagination - wrap in span for performance tracking
        with sentry_sdk.start_span(
            op="db.query", description="Execute ideas with scores query"
        ) as db_span:
            db_span.set_data(
                "status_filter",
                [s.value for s in status_filter]
                if isinstance(status_filter, list)
                else status_filter.value,
            )
            db_span.set_data("category_id", category_id)
            db_span.set_data("skip", skip)
            db_span.set_data("limit", limit)
            results = query.offset(skip).limit(limit).all()
            db_span.set_data("result_count", len(results))

        # Batch fetch all tags for returned ideas (fixes N+1 query)
        idea_ids = [r.Idea.id for r in results]
        with sentry_sdk.start_span(
            op="db.query", description="Batch fetch tags"
        ) as tags_span:
            tags_span.set_data("idea_count", len(idea_ids))
            tags_by_idea = self._fetch_tags_batch(idea_ids)

        # Batch fetch quality counts for returned ideas

        with sentry_sdk.start_span(
            op="db.query", description="Batch fetch quality counts"
        ) as quality_span:
            quality_span.set_data("idea_count", len(idea_ids))
            vote_quality_repo = VoteQualityRepository(self.db)
            quality_counts_by_idea = vote_quality_repo.get_counts_for_ideas_batch(
                idea_ids
            )

        # Format results
        ideas_with_scores = []
        for result in results:
            # Get tags from pre-fetched batch
            tags = tags_by_idea.get(result.Idea.id, [])

            # Get quality counts from pre-fetched batch
            idea_quality_data = quality_counts_by_idea.get(result.Idea.id, {})
            quality_counts = None
            if idea_quality_data.get("counts") or idea_quality_data.get(
                "total_votes_with_qualities", 0
            ):
                quality_counts = schemas.QualityCounts(
                    counts=[
                        schemas.QualityCount(**c) for c in idea_quality_data["counts"]
                    ],
                    total_votes_with_qualities=idea_quality_data[
                        "total_votes_with_qualities"
                    ],
                )

            idea_dict = {
                "id": result.Idea.id,
                "title": result.Idea.title,
                "description": result.Idea.description,
                "category_id": result.Idea.category_id,
                "user_id": result.Idea.user_id,
                "status": result.Idea.status,
                "admin_comment": result.Idea.admin_comment,
                "created_at": result.Idea.created_at,
                "validated_at": result.Idea.validated_at,
                "author_username": result.author_username,
                "author_display_name": result.author_display_name,
                "category_name_en": result.category_name_en,
                "category_name_fr": result.category_name_fr,
                "upvotes": result.upvotes,
                "downvotes": result.downvotes,
                "score": result.score,
                "comment_count": result.comment_count,
                "user_vote": result.user_vote if hasattr(result, "user_vote") else None,
                "quality_counts": quality_counts,
                "language": result.Idea.language,
                # Edit tracking fields
                "edit_count": result.Idea.edit_count,
                "last_edit_at": result.Idea.last_edit_at,
                "previous_status": result.Idea.previous_status,
                "tags": [
                    schemas.Tag(
                        id=int(tag.id),  # type: ignore[arg-type]
                        name=str(tag.name),  # type: ignore[arg-type]
                        display_name=str(tag.display_name),  # type: ignore[arg-type]
                        created_at=tag.created_at,  # type: ignore[arg-type]
                    )
                    for tag in tags
                ],
            }
            ideas_with_scores.append(schemas.IdeaWithScore(**idea_dict))

        return ideas_with_scores

    def get_ideas_by_tag_with_scores(
        self,
        tag_id: int,
        current_user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List["schemas.IdeaWithScore"]:
        """
        Get ideas with scores for a specific tag.

        Args:
            tag_id: Tag ID to filter by
            current_user_id: Current authenticated user ID (for user_vote field)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ideas with scores and vote information
        """
        import sentry_sdk

        import models.schemas as schemas

        sentry_sdk.set_tag("repo.method", "get_ideas_by_tag_with_scores")

        # Subquery for upvotes
        upvotes_subq = (
            self.db.query(
                db_models.Vote.idea_id,
                func.count(db_models.Vote.id).label("upvotes"),
            )
            .filter(db_models.Vote.vote_type == db_models.VoteType.UPVOTE)
            .group_by(db_models.Vote.idea_id)
            .subquery()
        )

        # Subquery for downvotes
        downvotes_subq = (
            self.db.query(
                db_models.Vote.idea_id,
                func.count(db_models.Vote.id).label("downvotes"),
            )
            .filter(db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE)
            .group_by(db_models.Vote.idea_id)
            .subquery()
        )

        # Subquery for comment count (only visible comments)
        comments_subq = (
            self.db.query(
                db_models.Comment.idea_id,
                func.count(db_models.Comment.id).label("comment_count"),
            )
            .filter(
                db_models.Comment.is_moderated.is_(False),
                db_models.Comment.deleted_at.is_(None),
                db_models.Comment.is_hidden.is_(False),
                db_models.Comment.requires_approval.is_(False),
            )
            .group_by(db_models.Comment.idea_id)
            .subquery()
        )

        # User vote subquery (if user is authenticated)
        user_vote_subq = None
        if current_user_id:
            user_vote_subq = (
                self.db.query(
                    db_models.Vote.idea_id,
                    db_models.Vote.vote_type.label("user_vote"),
                )
                .filter(db_models.Vote.user_id == current_user_id)
                .subquery()
            )

        # Main query - join with IdeaTag to filter by tag
        query = (
            self.db.query(
                db_models.Idea,
                db_models.User.username.label("author_username"),
                db_models.User.display_name.label("author_display_name"),
                db_models.Category.name_en.label("category_name_en"),
                db_models.Category.name_fr.label("category_name_fr"),
                func.coalesce(upvotes_subq.c.upvotes, 0).label("upvotes"),
                func.coalesce(downvotes_subq.c.downvotes, 0).label("downvotes"),
                (
                    func.coalesce(upvotes_subq.c.upvotes, 0)
                    - func.coalesce(downvotes_subq.c.downvotes, 0)
                ).label("score"),
                func.coalesce(comments_subq.c.comment_count, 0).label("comment_count"),
                user_vote_subq.c.user_vote
                if user_vote_subq is not None
                else literal(None).label("user_vote"),
            )
            .join(db_models.User, db_models.Idea.user_id == db_models.User.id)
            .join(
                db_models.Category,
                db_models.Idea.category_id == db_models.Category.id,
            )
            .join(db_models.IdeaTag, db_models.Idea.id == db_models.IdeaTag.idea_id)
            .outerjoin(upvotes_subq, db_models.Idea.id == upvotes_subq.c.idea_id)
            .outerjoin(downvotes_subq, db_models.Idea.id == downvotes_subq.c.idea_id)
            .outerjoin(comments_subq, db_models.Idea.id == comments_subq.c.idea_id)
        )

        if user_vote_subq is not None:
            query = query.outerjoin(
                user_vote_subq, db_models.Idea.id == user_vote_subq.c.idea_id
            )

        # Apply filters
        query = query.filter(
            db_models.IdeaTag.tag_id == tag_id,
            db_models.Idea.status == db_models.IdeaStatus.APPROVED,
            db_models.Idea.deleted_at.is_(None),
        )

        # Order by score (descending)
        query = query.order_by(
            (
                func.coalesce(upvotes_subq.c.upvotes, 0)
                - func.coalesce(downvotes_subq.c.downvotes, 0)
            ).desc(),
            db_models.Idea.created_at.desc(),
        )

        results = query.offset(skip).limit(limit).all()

        # Batch fetch all tags for returned ideas
        idea_ids = [r.Idea.id for r in results]
        tags_by_idea = self._fetch_tags_batch(idea_ids)

        # Batch fetch quality counts for returned ideas

        vote_quality_repo = VoteQualityRepository(self.db)
        quality_counts_by_idea = vote_quality_repo.get_counts_for_ideas_batch(idea_ids)

        # Format results
        ideas_with_scores = []
        for result in results:
            tags = tags_by_idea.get(result.Idea.id, [])

            # Get quality counts from pre-fetched batch
            idea_quality_data = quality_counts_by_idea.get(result.Idea.id, {})
            quality_counts = None
            if idea_quality_data.get("counts") or idea_quality_data.get(
                "total_votes_with_qualities", 0
            ):
                quality_counts = schemas.QualityCounts(
                    counts=[
                        schemas.QualityCount(**c) for c in idea_quality_data["counts"]
                    ],
                    total_votes_with_qualities=idea_quality_data[
                        "total_votes_with_qualities"
                    ],
                )

            idea_dict = {
                "id": result.Idea.id,
                "title": result.Idea.title,
                "description": result.Idea.description,
                "category_id": result.Idea.category_id,
                "user_id": result.Idea.user_id,
                "status": result.Idea.status,
                "admin_comment": result.Idea.admin_comment,
                "created_at": result.Idea.created_at,
                "validated_at": result.Idea.validated_at,
                "author_username": result.author_username,
                "author_display_name": result.author_display_name,
                "category_name_en": result.category_name_en,
                "category_name_fr": result.category_name_fr,
                "upvotes": result.upvotes,
                "downvotes": result.downvotes,
                "score": result.score,
                "user_vote": result.user_vote,
                "comment_count": result.comment_count,
                "quality_counts": quality_counts,
                "language": result.Idea.language,
                # Edit tracking fields
                "edit_count": result.Idea.edit_count,
                "last_edit_at": result.Idea.last_edit_at,
                "previous_status": result.Idea.previous_status,
                "tags": [
                    schemas.Tag(
                        id=int(tag.id),  # type: ignore[arg-type]
                        name=str(tag.name),  # type: ignore[arg-type]
                        display_name=str(tag.display_name),  # type: ignore[arg-type]
                        created_at=tag.created_at,  # type: ignore[arg-type]
                    )
                    for tag in tags
                ],
            }
            ideas_with_scores.append(schemas.IdeaWithScore(**idea_dict))

        return ideas_with_scores

    def get_by_category_and_status_for_admin(
        self,
        category_ids: List[int],
        status: db_models.IdeaStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.Idea]:
        """
        Get ideas by category IDs and status (for category admin filtering).

        Args:
            category_ids: List of category IDs
            status: Idea status
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of ideas
        """
        return (
            self.db.query(db_models.Idea)
            .filter(
                db_models.Idea.category_id.in_(category_ids),
                db_models.Idea.status == status,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_ideas_all_statuses(
        self,
        user_id: int,
        current_user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> List["schemas.IdeaWithScore"]:
        """
        Get all ideas for a user across all statuses in a single query.

        Orders by status priority (pending first) then by created_at desc.

        Args:
            user_id: User ID to fetch ideas for
            current_user_id: Current authenticated user ID (for user_vote)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of user's ideas with scores
        """
        import models.schemas as schemas

        # Subquery for upvotes
        upvotes_subq = (
            self.db.query(
                db_models.Vote.idea_id, func.count(db_models.Vote.id).label("upvotes")
            )
            .filter(db_models.Vote.vote_type == db_models.VoteType.UPVOTE)
            .group_by(db_models.Vote.idea_id)
            .subquery()
        )

        # Subquery for downvotes
        downvotes_subq = (
            self.db.query(
                db_models.Vote.idea_id, func.count(db_models.Vote.id).label("downvotes")
            )
            .filter(db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE)
            .group_by(db_models.Vote.idea_id)
            .subquery()
        )

        # Subquery for comment count (only visible comments)
        comments_subq = (
            self.db.query(
                db_models.Comment.idea_id,
                func.count(db_models.Comment.id).label("comment_count"),
            )
            .filter(
                db_models.Comment.is_moderated.is_(False),
                db_models.Comment.deleted_at.is_(None),
                db_models.Comment.is_hidden.is_(False),
                db_models.Comment.requires_approval.is_(False),
            )
            .group_by(db_models.Comment.idea_id)
            .subquery()
        )

        # User vote subquery
        user_vote_subq = (
            self.db.query(
                db_models.Vote.idea_id, db_models.Vote.vote_type.label("user_vote")
            )
            .filter(db_models.Vote.user_id == current_user_id)
            .subquery()
        )

        # Status priority ordering: pending=0, pending_edit=1, approved=2, rejected=3
        status_order = case(
            (db_models.Idea.status == db_models.IdeaStatus.PENDING, 0),
            (db_models.Idea.status == db_models.IdeaStatus.PENDING_EDIT, 1),
            (db_models.Idea.status == db_models.IdeaStatus.APPROVED, 2),
            (db_models.Idea.status == db_models.IdeaStatus.REJECTED, 3),
            else_=4,
        )

        # Main query - no status filter, just user filter, exclude deleted
        query = (
            self.db.query(
                db_models.Idea,
                db_models.User.username.label("author_username"),
                db_models.User.display_name.label("author_display_name"),
                db_models.Category.name_en.label("category_name_en"),
                db_models.Category.name_fr.label("category_name_fr"),
                func.coalesce(upvotes_subq.c.upvotes, 0).label("upvotes"),
                func.coalesce(downvotes_subq.c.downvotes, 0).label("downvotes"),
                (
                    func.coalesce(upvotes_subq.c.upvotes, 0)
                    - func.coalesce(downvotes_subq.c.downvotes, 0)
                ).label("score"),
                func.coalesce(comments_subq.c.comment_count, 0).label("comment_count"),
                user_vote_subq.c.user_vote,
            )
            .join(db_models.User, db_models.Idea.user_id == db_models.User.id)
            .join(
                db_models.Category, db_models.Idea.category_id == db_models.Category.id
            )
            .outerjoin(upvotes_subq, db_models.Idea.id == upvotes_subq.c.idea_id)
            .outerjoin(downvotes_subq, db_models.Idea.id == downvotes_subq.c.idea_id)
            .outerjoin(comments_subq, db_models.Idea.id == comments_subq.c.idea_id)
            .outerjoin(user_vote_subq, db_models.Idea.id == user_vote_subq.c.idea_id)
            .filter(
                db_models.Idea.user_id == user_id,
                db_models.Idea.deleted_at.is_(None),
            )
            .order_by(status_order, db_models.Idea.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        results = query.all()

        # Batch fetch tags
        idea_ids = [r.Idea.id for r in results]
        tags_by_idea = self._fetch_tags_batch(idea_ids)

        # Batch fetch quality counts for returned ideas

        vote_quality_repo = VoteQualityRepository(self.db)
        quality_counts_by_idea = vote_quality_repo.get_counts_for_ideas_batch(idea_ids)

        # Format results
        ideas_with_scores = []
        for result in results:
            tags = tags_by_idea.get(result.Idea.id, [])

            # Get quality counts from pre-fetched batch
            idea_quality_data = quality_counts_by_idea.get(result.Idea.id, {})
            quality_counts = None
            if idea_quality_data.get("counts") or idea_quality_data.get(
                "total_votes_with_qualities", 0
            ):
                quality_counts = schemas.QualityCounts(
                    counts=[
                        schemas.QualityCount(**c) for c in idea_quality_data["counts"]
                    ],
                    total_votes_with_qualities=idea_quality_data[
                        "total_votes_with_qualities"
                    ],
                )

            idea_dict = {
                "id": result.Idea.id,
                "title": result.Idea.title,
                "description": result.Idea.description,
                "category_id": result.Idea.category_id,
                "user_id": result.Idea.user_id,
                "status": result.Idea.status,
                "admin_comment": result.Idea.admin_comment,
                "created_at": result.Idea.created_at,
                "validated_at": result.Idea.validated_at,
                "author_username": result.author_username,
                "author_display_name": result.author_display_name,
                "category_name_en": result.category_name_en,
                "category_name_fr": result.category_name_fr,
                "upvotes": result.upvotes,
                "downvotes": result.downvotes,
                "score": result.score,
                "comment_count": result.comment_count,
                "user_vote": result.user_vote if hasattr(result, "user_vote") else None,
                "quality_counts": quality_counts,
                "language": result.Idea.language,
                # Edit tracking fields
                "edit_count": result.Idea.edit_count,
                "last_edit_at": result.Idea.last_edit_at,
                "previous_status": result.Idea.previous_status,
                "tags": [
                    schemas.Tag(
                        id=int(tag.id),  # type: ignore[arg-type]
                        name=str(tag.name),  # type: ignore[arg-type]
                        display_name=str(tag.display_name),  # type: ignore[arg-type]
                        created_at=tag.created_at,  # type: ignore[arg-type]
                    )
                    for tag in tags
                ],
            }
            ideas_with_scores.append(schemas.IdeaWithScore(**idea_dict))

        return ideas_with_scores

    def get_ideas_by_ids_with_scores(
        self,
        idea_ids: list[int],
        current_user_id: Optional[int] = None,
    ) -> List["schemas.IdeaWithScore"]:
        """
        Get ideas by IDs with vote scores and comment counts.

        Preserves the order of idea_ids for relevance-sorted results
        (important for search results).

        Args:
            idea_ids: List of idea IDs to fetch
            current_user_id: Optional user ID for vote status

        Returns:
            List of IdeaWithScore objects in the same order as idea_ids
        """
        import models.schemas as schemas

        if not idea_ids:
            return []

        # Subquery for upvotes
        upvotes_subq = (
            self.db.query(
                db_models.Vote.idea_id, func.count(db_models.Vote.id).label("upvotes")
            )
            .filter(db_models.Vote.vote_type == db_models.VoteType.UPVOTE)
            .group_by(db_models.Vote.idea_id)
            .subquery()
        )

        # Subquery for downvotes
        downvotes_subq = (
            self.db.query(
                db_models.Vote.idea_id, func.count(db_models.Vote.id).label("downvotes")
            )
            .filter(db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE)
            .group_by(db_models.Vote.idea_id)
            .subquery()
        )

        # Subquery for comment count (only visible comments)
        comments_subq = (
            self.db.query(
                db_models.Comment.idea_id,
                func.count(db_models.Comment.id).label("comment_count"),
            )
            .filter(
                db_models.Comment.is_moderated.is_(False),
                db_models.Comment.deleted_at.is_(None),
                db_models.Comment.is_hidden.is_(False),
                db_models.Comment.requires_approval.is_(False),
            )
            .group_by(db_models.Comment.idea_id)
            .subquery()
        )

        # User vote subquery (if user is authenticated)
        user_vote_subq = None
        if current_user_id:
            user_vote_subq = (
                self.db.query(
                    db_models.Vote.idea_id, db_models.Vote.vote_type.label("user_vote")
                )
                .filter(db_models.Vote.user_id == current_user_id)
                .subquery()
            )

        # Main query - fetch by IDs
        query = (
            self.db.query(
                db_models.Idea,
                db_models.User.username.label("author_username"),
                db_models.User.display_name.label("author_display_name"),
                db_models.Category.name_en.label("category_name_en"),
                db_models.Category.name_fr.label("category_name_fr"),
                func.coalesce(upvotes_subq.c.upvotes, 0).label("upvotes"),
                func.coalesce(downvotes_subq.c.downvotes, 0).label("downvotes"),
                (
                    func.coalesce(upvotes_subq.c.upvotes, 0)
                    - func.coalesce(downvotes_subq.c.downvotes, 0)
                ).label("score"),
                func.coalesce(comments_subq.c.comment_count, 0).label("comment_count"),
                user_vote_subq.c.user_vote
                if user_vote_subq is not None
                else literal(None).label("user_vote"),
            )
            .join(db_models.User, db_models.Idea.user_id == db_models.User.id)
            .join(
                db_models.Category, db_models.Idea.category_id == db_models.Category.id
            )
            .outerjoin(upvotes_subq, db_models.Idea.id == upvotes_subq.c.idea_id)
            .outerjoin(downvotes_subq, db_models.Idea.id == downvotes_subq.c.idea_id)
            .outerjoin(comments_subq, db_models.Idea.id == comments_subq.c.idea_id)
            .filter(
                db_models.Idea.id.in_(idea_ids),
                db_models.Idea.deleted_at.is_(None),
            )
        )

        if user_vote_subq is not None:
            query = query.outerjoin(
                user_vote_subq, db_models.Idea.id == user_vote_subq.c.idea_id
            )

        results = query.all()

        # Batch fetch tags
        tags_by_idea = self._fetch_tags_batch(idea_ids)

        # Batch fetch quality counts for returned ideas

        vote_quality_repo = VoteQualityRepository(self.db)
        quality_counts_by_idea = vote_quality_repo.get_counts_for_ideas_batch(idea_ids)

        # Build ideas_by_id dict for preserving order
        ideas_by_id: dict[int, schemas.IdeaWithScore] = {}
        for result in results:
            tags = tags_by_idea.get(result.Idea.id, [])

            # Get quality counts from pre-fetched batch
            idea_quality_data = quality_counts_by_idea.get(result.Idea.id, {})
            quality_counts = None
            if idea_quality_data.get("counts") or idea_quality_data.get(
                "total_votes_with_qualities", 0
            ):
                quality_counts = schemas.QualityCounts(
                    counts=[
                        schemas.QualityCount(**c) for c in idea_quality_data["counts"]
                    ],
                    total_votes_with_qualities=idea_quality_data[
                        "total_votes_with_qualities"
                    ],
                )

            idea_dict = {
                "id": result.Idea.id,
                "title": result.Idea.title,
                "description": result.Idea.description,
                "category_id": result.Idea.category_id,
                "user_id": result.Idea.user_id,
                "status": result.Idea.status,
                "admin_comment": result.Idea.admin_comment,
                "created_at": result.Idea.created_at,
                "validated_at": result.Idea.validated_at,
                "author_username": result.author_username,
                "author_display_name": result.author_display_name,
                "category_name_en": result.category_name_en,
                "category_name_fr": result.category_name_fr,
                "upvotes": result.upvotes,
                "downvotes": result.downvotes,
                "score": result.score,
                "comment_count": result.comment_count,
                "user_vote": result.user_vote if hasattr(result, "user_vote") else None,
                "quality_counts": quality_counts,
                "language": result.Idea.language,
                # Edit tracking fields
                "edit_count": result.Idea.edit_count,
                "last_edit_at": result.Idea.last_edit_at,
                "previous_status": result.Idea.previous_status,
                "tags": [
                    schemas.Tag(
                        id=int(tag.id),  # type: ignore[arg-type]
                        name=str(tag.name),  # type: ignore[arg-type]
                        display_name=str(tag.display_name),  # type: ignore[arg-type]
                        created_at=tag.created_at,  # type: ignore[arg-type]
                    )
                    for tag in tags
                ],
            }
            ideas_by_id[result.Idea.id] = schemas.IdeaWithScore(**idea_dict)

        # Return in original order (preserves relevance ranking from search)
        return [ideas_by_id[id] for id in idea_ids if id in ideas_by_id]

    # Soft delete methods

    def get_by_id_with_deleted(
        self, idea_id: int, include_deleted: bool = False
    ) -> Optional[db_models.Idea]:
        """
        Get idea by ID, optionally including deleted ideas.

        Args:
            idea_id: Idea ID
            include_deleted: Whether to include deleted ideas

        Returns:
            Idea or None if not found
        """
        query = self.db.query(db_models.Idea).filter(db_models.Idea.id == idea_id)
        if not include_deleted:
            query = query.filter(db_models.Idea.deleted_at.is_(None))
        return query.first()

    def get_deleted_by_id(self, idea_id: int) -> Optional[db_models.Idea]:
        """
        Get a deleted idea by ID (admin only).

        Args:
            idea_id: Idea ID

        Returns:
            Deleted idea or None
        """
        return (
            self.db.query(db_models.Idea)
            .filter(
                db_models.Idea.id == idea_id,
                db_models.Idea.deleted_at.isnot(None),
            )
            .first()
        )

    def soft_delete(
        self,
        idea: db_models.Idea,
        deleted_by_id: int,
        reason: Optional[str] = None,
    ) -> db_models.Idea:
        """
        Soft delete an idea.

        Args:
            idea: Idea to delete
            deleted_by_id: User ID of the person deleting
            reason: Optional reason for deletion

        Returns:
            The deleted idea
        """
        from datetime import datetime, timezone

        idea.deleted_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        idea.deleted_by = deleted_by_id  # type: ignore[assignment]
        idea.deletion_reason = reason  # type: ignore[assignment]
        self.db.commit()
        self.db.refresh(idea)
        return idea

    def restore(self, idea: db_models.Idea) -> db_models.Idea:
        """
        Restore a soft-deleted idea.

        Args:
            idea: Idea to restore

        Returns:
            The restored idea
        """
        idea.deleted_at = None  # type: ignore[assignment]
        idea.deleted_by = None  # type: ignore[assignment]
        idea.deletion_reason = None  # type: ignore[assignment]
        self.db.commit()
        self.db.refresh(idea)
        return idea

    def get_deleted_ideas(
        self, skip: int = 0, limit: int = 20
    ) -> tuple[list[db_models.Idea], int]:
        """
        Get paginated list of deleted ideas (admin only).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (ideas, total_count)
        """
        query = self.db.query(db_models.Idea).filter(
            db_models.Idea.deleted_at.isnot(None)
        )
        total = query.count()
        ideas = (
            query.order_by(db_models.Idea.deleted_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return ideas, total

    def get_rejected_ideas(
        self, skip: int = 0, limit: int = 20
    ) -> tuple[list[db_models.Idea], int]:
        """
        Get paginated list of rejected ideas (admin only).

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (ideas, total_count)
        """
        query = self.db.query(db_models.Idea).filter(
            db_models.Idea.status == db_models.IdeaStatus.REJECTED,
            db_models.Idea.deleted_at.is_(None),  # Exclude soft-deleted
        )
        total = query.count()
        ideas = (
            query.order_by(db_models.Idea.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return ideas, total

    def count_pending_ideas(
        self,
        category_ids: Optional[List[int]] = None,
    ) -> int:
        """
        Count pending ideas (PENDING and PENDING_EDIT), optionally filtered by category IDs.

        Args:
            category_ids: Optional list of category IDs to filter by.
                         If None, counts all pending ideas.

        Returns:
            Total count of pending ideas matching criteria.
        """
        # Include both PENDING and PENDING_EDIT for admin moderation queue
        query = self.db.query(func.count(db_models.Idea.id)).filter(
            db_models.Idea.status.in_(
                [db_models.IdeaStatus.PENDING, db_models.IdeaStatus.PENDING_EDIT]
            ),
            db_models.Idea.deleted_at.is_(None),
        )

        if category_ids:
            query = query.filter(db_models.Idea.category_id.in_(category_ids))

        result = query.scalar()
        return result if result is not None else 0

    def delete_by_user_id(self, user_id: int) -> int:
        """
        Delete all ideas by a user.

        Args:
            user_id: User ID

        Returns:
            Number of deleted records
        """
        count = (
            self.db.query(db_models.Idea)
            .filter(db_models.Idea.user_id == user_id)
            .delete()
        )
        return count

    def get_approved_idea_ids(self) -> list[int]:
        """
        Get all approved idea IDs.

        Returns:
            List of approved idea IDs
        """
        results = (
            self.db.query(db_models.Idea.id)
            .filter(
                db_models.Idea.status == db_models.IdeaStatus.APPROVED,
                db_models.Idea.deleted_at.is_(None),
            )
            .all()
        )
        return [r[0] for r in results]

    def count_by_category(
        self, category_id: int, status: db_models.IdeaStatus | None = None
    ) -> int:
        """
        Count ideas by category with optional status filter.

        Args:
            category_id: Category ID
            status: Optional status filter

        Returns:
            Count of ideas
        """
        query = self.db.query(func.count(db_models.Idea.id)).filter(
            db_models.Idea.category_id == category_id
        )

        if status:
            query = query.filter(db_models.Idea.status == status)

        result = query.scalar()
        return result if result is not None else 0

    def get_sitemap_data(self) -> list[tuple[int, Optional[datetime], int]]:
        """
        Get minimal idea data for sitemap generation.

        Returns:
            List of tuples (id, updated_at, score) for approved ideas
        """

        results = (
            self.db.query(
                db_models.Idea.id,
                func.coalesce(
                    db_models.Idea.validated_at, db_models.Idea.created_at
                ).label("updated_at"),
                func.coalesce(db_models.Idea.score, 0).label("score"),
            )
            .filter(
                db_models.Idea.status == db_models.IdeaStatus.APPROVED,
                db_models.Idea.deleted_at.is_(None),
            )
            .order_by(db_models.Idea.score.desc())
            .all()
        )
        return [(r.id, r.updated_at, r.score) for r in results]

    def search_by_keywords(
        self,
        keywords: set[str],
        category_id: Optional[int] = None,
        limit: int = 25,
    ) -> List[db_models.Idea]:
        """
        Search approved ideas matching any of the given keywords.

        Args:
            keywords: Set of keywords to match (case-insensitive)
            category_id: Optional category filter
            limit: Maximum number of results

        Returns:
            List of matching ideas
        """
        from sqlalchemy import or_

        if not keywords:
            return []

        # Build OR conditions for keyword matching (max 10 keywords)
        conditions = []
        for keyword in list(keywords)[:10]:
            conditions.append(db_models.Idea.title.ilike(f"%{keyword}%"))
            conditions.append(db_models.Idea.description.ilike(f"%{keyword}%"))

        if not conditions:
            return []

        query = (
            self.db.query(db_models.Idea)
            .filter(db_models.Idea.status == db_models.IdeaStatus.APPROVED)
            .filter(or_(*conditions))
        )

        if category_id:
            query = query.filter(db_models.Idea.category_id == category_id)

        return query.limit(limit).all()

    def get_with_author(self, idea_id: int) -> Any | None:
        """
        Get idea with its author.

        Args:
            idea_id: Idea ID

        Returns:
            Tuple of (Idea, User) or None if not found
        """
        return (
            self.db.query(db_models.Idea, db_models.User)
            .join(db_models.User, db_models.Idea.user_id == db_models.User.id)
            .filter(db_models.Idea.id == idea_id)
            .first()
        )

    def unhide(self, idea_id: int) -> bool:
        """
        Unhide an idea and reset flag count.

        Args:
            idea_id: Idea ID

        Returns:
            True if updated, False if not found
        """
        idea = self.get_by_id(idea_id)
        if not idea:
            return False

        idea.is_hidden = False  # type: ignore[assignment]
        idea.hidden_at = None  # type: ignore[assignment]
        idea.flag_count = 0  # type: ignore[assignment]
        self.commit()
        return True

    def soft_delete_for_moderation(
        self,
        idea_id: int,
        deleted_by: int,
        reason: str,
    ) -> int | None:
        """
        Soft delete an idea for moderation.

        Args:
            idea_id: Idea ID
            deleted_by: ID of user performing deletion
            reason: Deletion reason

        Returns:
            Author ID if deleted, None if not found
        """
        idea = self.get_by_id(idea_id)
        if not idea:
            return None

        author_id = int(idea.user_id)
        idea.deleted_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        idea.deleted_by = deleted_by  # type: ignore[assignment]
        idea.deletion_reason = reason  # type: ignore[assignment]
        self.commit()
        return author_id

    def get_by_status_filtered(
        self,
        status: db_models.IdeaStatus,
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.Idea]:
        """
        Get ideas by status excluding deleted, with optional category filter.

        Args:
            status: Idea status
            category_id: Optional category filter
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of ideas (excludes deleted)
        """
        query = self.db.query(db_models.Idea).filter(
            db_models.Idea.status == status,
            db_models.Idea.deleted_at.is_(None),
        )

        if category_id:
            query = query.filter(db_models.Idea.category_id == category_id)

        return (
            query.order_by(db_models.Idea.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_excluding_deleted(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.Idea]:
        """
        Get ideas by user excluding deleted.

        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of ideas (excludes deleted)
        """
        return (
            self.db.query(db_models.Idea)
            .filter(
                db_models.Idea.user_id == user_id,
                db_models.Idea.deleted_at.is_(None),
            )
            .order_by(db_models.Idea.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def bulk_update_comments_idea_id(
        self,
        source_idea_id: int,
        target_idea_id: int,
    ) -> int:
        """
        Update all comments from one idea to another (for merge).

        Args:
            source_idea_id: Source idea ID
            target_idea_id: Target idea ID

        Returns:
            Number of comments updated
        """
        return (
            self.db.query(db_models.Comment)
            .filter(db_models.Comment.idea_id == source_idea_id)
            .update({"idea_id": target_idea_id})
        )

    def search_basic(
        self,
        search_term: str,
        category_id: Optional[int] = None,
        status: Optional[db_models.IdeaStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.Idea]:
        """
        Basic keyword search in title and description.

        Args:
            search_term: Escaped search term (use escape_like first)
            category_id: Optional category filter
            status: Optional status filter
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of matching ideas
        """
        from sqlalchemy import or_

        search_filter = or_(
            db_models.Idea.title.ilike(f"%{search_term}%", escape="\\"),
            db_models.Idea.description.ilike(f"%{search_term}%", escape="\\"),
        )

        query = self.db.query(db_models.Idea).filter(
            search_filter,
            db_models.Idea.deleted_at.is_(None),
        )

        if category_id:
            query = query.filter(db_models.Idea.category_id == category_id)

        if status:
            query = query.filter(db_models.Idea.status == status)

        return (
            query.order_by(db_models.Idea.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_vote_statistics(self, idea_id: int) -> dict[str, int]:
        """
        Get vote statistics for an idea.

        Args:
            idea_id: Idea ID

        Returns:
            Dict with upvotes, downvotes counts
        """
        upvotes = (
            self.db.query(func.count(db_models.Vote.id))
            .filter(
                db_models.Vote.idea_id == idea_id,
                db_models.Vote.vote_type == db_models.VoteType.UPVOTE,
            )
            .scalar()
            or 0
        )

        downvotes = (
            self.db.query(func.count(db_models.Vote.id))
            .filter(
                db_models.Vote.idea_id == idea_id,
                db_models.Vote.vote_type == db_models.VoteType.DOWNVOTE,
            )
            .scalar()
            or 0
        )

        return {"upvotes": upvotes, "downvotes": downvotes}

    def get_comment_count(self, idea_id: int) -> int:
        """
        Get comment count for an idea.

        Args:
            idea_id: Idea ID

        Returns:
            Number of comments
        """
        return (
            self.db.query(func.count(db_models.Comment.id))
            .filter(db_models.Comment.idea_id == idea_id)
            .scalar()
            or 0
        )

    def get_approved_with_quality_filter(
        self,
        quality_id: int,
        min_quality_count: int,
        category_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[int]:
        """
        Get approved idea IDs that meet quality filter criteria.

        Args:
            quality_id: Quality ID to filter by
            min_quality_count: Minimum number of votes with this quality
            category_id: Optional category filter
            skip: Pagination offset
            limit: Pagination limit

        Returns:
            List of idea IDs ordered by quality count descending
        """
        # Subquery for quality count per idea
        quality_subq = (
            self.db.query(
                db_models.Vote.idea_id,
                func.count(db_models.VoteQuality.id).label("quality_count"),
            )
            .join(
                db_models.VoteQuality,
                db_models.VoteQuality.vote_id == db_models.Vote.id,
            )
            .filter(db_models.VoteQuality.quality_id == quality_id)
            .filter(db_models.Vote.vote_type == db_models.VoteType.UPVOTE)
            .group_by(db_models.Vote.idea_id)
            .having(func.count(db_models.VoteQuality.id) >= min_quality_count)
            .subquery()
        )

        # Get matching idea IDs
        query = (
            self.db.query(db_models.Idea.id)
            .join(quality_subq, quality_subq.c.idea_id == db_models.Idea.id)
            .filter(db_models.Idea.status == db_models.IdeaStatus.APPROVED)
            .filter(db_models.Idea.deleted_at.is_(None))
        )

        if category_id:
            query = query.filter(db_models.Idea.category_id == category_id)

        # Order by quality count descending
        query = query.order_by(quality_subq.c.quality_count.desc())
        return [row[0] for row in query.offset(skip).limit(limit).all()]

    def bulk_soft_delete_by_user(
        self,
        user_id: int,
        deleted_by: int,
        reason: str,
    ) -> int:
        """
        Soft delete all non-deleted ideas by a user.

        Used when banning a user.

        Args:
            user_id: User ID whose ideas to delete
            deleted_by: ID of admin performing deletion
            reason: Deletion reason

        Returns:
            Number of ideas deleted
        """
        now = datetime.now(timezone.utc)
        result = (
            self.db.query(db_models.Idea)
            .filter(
                db_models.Idea.user_id == user_id,
                db_models.Idea.deleted_at.is_(None),
            )
            .update(
                {
                    db_models.Idea.deleted_at: now,
                    db_models.Idea.deleted_by: deleted_by,
                    db_models.Idea.deletion_reason: reason,
                },
                synchronize_session=False,
            )
        )
        return result

    # ========================================================================
    # Edit Tracking Methods (for edit-approved-ideas workflow)
    # ========================================================================

    def get_edit_count_this_month(self, idea_id: int) -> int:
        """
        Get the number of edits for an idea in the current month.

        Note: We track edit_count as a running total on the idea, and
        reset it monthly based on last_edit_at timestamp. If last_edit_at
        is in a previous month, we return 0.

        Args:
            idea_id: Idea ID

        Returns:
            Number of edits this month (0 if never edited or last edit was last month)
        """
        idea = self.get_by_id(idea_id)
        if not idea:
            return 0

        # If never edited, return 0
        if idea.last_edit_at is None:
            return 0

        # Check if last edit was in current month
        now = datetime.now(timezone.utc)
        last_edit = idea.last_edit_at
        if hasattr(last_edit, "tzinfo") and last_edit.tzinfo is None:
            # Make naive datetime UTC-aware for comparison
            from datetime import timezone as tz

            last_edit = last_edit.replace(tzinfo=tz.utc)

        if last_edit.year == now.year and last_edit.month == now.month:
            return int(idea.edit_count)

        # Last edit was in a different month, so count resets
        return 0

    def update_edit_tracking(
        self,
        idea: db_models.Idea,
        previous_status: str,
    ) -> db_models.Idea:
        """
        Update edit tracking fields when an approved idea is edited.

        This method:
        - Increments edit_count (or resets to 1 if new month)
        - Updates last_edit_at to now
        - Stores previous_status for potential restoration
        - Transitions status to PENDING_EDIT

        Args:
            idea: Idea to update
            previous_status: Status before edit (e.g., 'approved')

        Returns:
            Updated idea
        """
        now = datetime.now(timezone.utc)

        # Check if we need to reset edit count (new month)
        if idea.last_edit_at is not None:
            last_edit = idea.last_edit_at
            if hasattr(last_edit, "tzinfo") and last_edit.tzinfo is None:
                from datetime import timezone as tz

                last_edit = last_edit.replace(tzinfo=tz.utc)

            if last_edit.year == now.year and last_edit.month == now.month:
                # Same month, increment
                idea.edit_count = int(idea.edit_count) + 1  # type: ignore[assignment]
            else:
                # New month, reset to 1
                idea.edit_count = 1  # type: ignore[assignment]
        else:
            # First edit ever
            idea.edit_count = 1  # type: ignore[assignment]

        idea.last_edit_at = now  # type: ignore[assignment]
        idea.previous_status = previous_status  # type: ignore[assignment]
        idea.status = db_models.IdeaStatus.PENDING_EDIT  # type: ignore[assignment]

        self.commit()
        self.refresh(idea)
        return idea

    def get_pending_edits(
        self,
        category_ids: Optional[List[int]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[db_models.Idea]:
        """
        Get ideas with PENDING_EDIT status for admin moderation queue.

        Args:
            category_ids: Optional list of category IDs to filter by
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of ideas pending edit review
        """
        query = self.db.query(db_models.Idea).filter(
            db_models.Idea.status == db_models.IdeaStatus.PENDING_EDIT,
            db_models.Idea.deleted_at.is_(None),
        )

        if category_ids:
            query = query.filter(db_models.Idea.category_id.in_(category_ids))

        return (
            query.order_by(db_models.Idea.last_edit_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_pending_edits(
        self,
        category_ids: Optional[List[int]] = None,
    ) -> int:
        """
        Count ideas with PENDING_EDIT status.

        Args:
            category_ids: Optional list of category IDs to filter by

        Returns:
            Total count of ideas pending edit review
        """
        query = self.db.query(func.count(db_models.Idea.id)).filter(
            db_models.Idea.status == db_models.IdeaStatus.PENDING_EDIT,
            db_models.Idea.deleted_at.is_(None),
        )

        if category_ids:
            query = query.filter(db_models.Idea.category_id.in_(category_ids))

        result = query.scalar()
        return result if result is not None else 0

    def restore_previous_status(
        self,
        idea: db_models.Idea,
    ) -> db_models.Idea:
        """
        Restore idea to its previous status after edit approval.

        This method restores the status stored in previous_status
        (typically APPROVED) and clears the previous_status field.

        Args:
            idea: Idea to restore

        Returns:
            Updated idea with restored status
        """
        if idea.previous_status:
            # Map string back to enum
            status_map = {
                "pending": db_models.IdeaStatus.PENDING,
                "approved": db_models.IdeaStatus.APPROVED,
                "rejected": db_models.IdeaStatus.REJECTED,
                "pending_edit": db_models.IdeaStatus.PENDING_EDIT,
            }
            restored_status = status_map.get(
                idea.previous_status.lower(),
                db_models.IdeaStatus.APPROVED,
            )
            idea.status = restored_status  # type: ignore[assignment]

        idea.previous_status = None  # type: ignore[assignment]
        idea.validated_at = datetime.now(timezone.utc)  # type: ignore[assignment]

        self.commit()
        self.refresh(idea)
        return idea
