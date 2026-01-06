"""
Analytics Repository - Optimized queries for dashboard metrics.

This repository handles all database aggregations for the analytics dashboard.
Uses SQLAlchemy func.* for efficient database-level calculations.

ARCHITECTURAL NOTE:
This repository intentionally does NOT extend BaseRepository[T] because:
1. It aggregates data across multiple entities (User, Idea, Vote, Comment, Category)
2. It performs read-only aggregation queries, not CRUD operations
3. BaseRepository methods (get_by_id, create, update, delete) are not applicable
4. All methods are stateless aggregations suitable for static methods

This is an accepted deviation from the standard repository pattern.
See: ARCH-2030-004 in claude-docs/mgt/BUGS.md
"""

from datetime import datetime, timedelta, timezone
from typing import Any  # noqa: F401 - used in type annotations

from sqlalchemy import and_, case, func, literal_column
from sqlalchemy.orm import Session

from models.config import settings
from repositories.db_models import (
    Category,
    Comment,
    Idea,
    IdeaStatus,
    User,
    Vote,
    VoteType,
)


def _is_postgresql() -> bool:
    """Check if the database is PostgreSQL."""
    return settings.DATABASE_URL.startswith("postgresql")


def _format_week(column: Any) -> Any:
    """
    Format a datetime column as year-week string (YYYY-WXX).

    Uses to_char for PostgreSQL and strftime for SQLite.
    """
    if _is_postgresql():
        # PostgreSQL: to_char with ISO week (IW) and year for ISO week (IYYY)
        return func.to_char(column, literal_column("'IYYY-\"W\"IW'"))
    else:
        # SQLite: strftime with %W for week number
        return func.strftime("%Y-W%W", column)


def _format_month(column: Any) -> Any:
    """
    Format a datetime column as year-month string (YYYY-MM).

    Uses to_char for PostgreSQL and strftime for SQLite.
    """
    if _is_postgresql():
        return func.to_char(column, literal_column("'YYYY-MM'"))
    else:
        return func.strftime("%Y-%m", column)


class AnalyticsRepository:
    """Repository for analytics data aggregation."""

    @staticmethod
    def get_overview_counts(db: Session) -> dict[str, int]:
        """
        Get all overview counts in minimal queries.

        Returns dict with: total_users, active_users, idea counts by status,
        total_votes, total_comments.
        """
        # User counts - single query
        user_counts = db.query(
            func.count(User.id).label("total"),
            func.sum(case((User.is_active == True, 1), else_=0)).label("active"),  # noqa: E712
        ).first()

        # Idea counts by status - single query
        idea_counts = (
            db.query(
                func.count(Idea.id).label("total"),
                func.sum(case((Idea.status == IdeaStatus.APPROVED, 1), else_=0)).label(
                    "approved"
                ),
                func.sum(case((Idea.status == IdeaStatus.PENDING, 1), else_=0)).label(
                    "pending"
                ),
                func.sum(case((Idea.status == IdeaStatus.REJECTED, 1), else_=0)).label(
                    "rejected"
                ),
            )
            .filter(Idea.deleted_at.is_(None))
            .first()
        )

        # Vote count
        vote_count = db.query(func.count(Vote.id)).scalar() or 0

        # Comment count
        comment_count = db.query(func.count(Comment.id)).scalar() or 0

        return {
            "total_users": int(user_counts.total or 0) if user_counts else 0,
            "active_users": int(user_counts.active or 0) if user_counts else 0,
            "total_ideas": int(idea_counts.total or 0) if idea_counts else 0,
            "approved_ideas": int(idea_counts.approved or 0) if idea_counts else 0,
            "pending_ideas": int(idea_counts.pending or 0) if idea_counts else 0,
            "rejected_ideas": int(idea_counts.rejected or 0) if idea_counts else 0,
            "total_votes": vote_count,
            "total_comments": comment_count,
        }

    @staticmethod
    def get_this_week_counts(db: Session) -> dict[str, int]:
        """
        Get counts for the current week (last 7 days).

        Returns dict with: ideas_this_week, votes_this_week,
        comments_this_week, users_this_week.
        """
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        ideas_this_week = (
            db.query(func.count(Idea.id))
            .filter(and_(Idea.created_at >= week_ago, Idea.deleted_at.is_(None)))
            .scalar()
            or 0
        )

        votes_this_week = (
            db.query(func.count(Vote.id)).filter(Vote.created_at >= week_ago).scalar()
            or 0
        )

        comments_this_week = (
            db.query(func.count(Comment.id))
            .filter(Comment.created_at >= week_ago)
            .scalar()
            or 0
        )

        users_this_week = (
            db.query(func.count(User.id)).filter(User.created_at >= week_ago).scalar()
            or 0
        )

        return {
            "ideas_this_week": ideas_this_week,
            "votes_this_week": votes_this_week,
            "comments_this_week": comments_this_week,
            "users_this_week": users_this_week,
        }

    @staticmethod
    def get_daily_trends(
        db: Session, start_date: datetime, end_date: datetime
    ) -> list[dict[str, Any]]:
        """
        Get daily aggregated counts for trends chart.

        Groups by date, returns list of dicts with date and counts.
        """
        # Ideas per day
        ideas_by_day = (
            db.query(
                func.date(Idea.created_at).label("date"),
                func.count(Idea.id).label("count"),
            )
            .filter(
                and_(
                    Idea.created_at >= start_date,
                    Idea.created_at <= end_date,
                    Idea.deleted_at.is_(None),
                )
            )
            .group_by(func.date(Idea.created_at))
            .all()
        )

        # Votes per day
        votes_by_day = (
            db.query(
                func.date(Vote.created_at).label("date"),
                func.count(Vote.id).label("count"),
            )
            .filter(and_(Vote.created_at >= start_date, Vote.created_at <= end_date))
            .group_by(func.date(Vote.created_at))
            .all()
        )

        # Comments per day
        comments_by_day = (
            db.query(
                func.date(Comment.created_at).label("date"),
                func.count(Comment.id).label("count"),
            )
            .filter(
                and_(Comment.created_at >= start_date, Comment.created_at <= end_date)
            )
            .group_by(func.date(Comment.created_at))
            .all()
        )

        # Users per day
        users_by_day = (
            db.query(
                func.date(User.created_at).label("date"),
                func.count(User.id).label("count"),
            )
            .filter(and_(User.created_at >= start_date, User.created_at <= end_date))
            .group_by(func.date(User.created_at))
            .all()
        )

        # Combine into unified structure
        return AnalyticsRepository._merge_daily_data(
            ideas_by_day,
            votes_by_day,
            comments_by_day,
            users_by_day,
            start_date,
            end_date,
        )

    @staticmethod
    def _merge_daily_data(
        ideas: list,
        votes: list,
        comments: list,
        users: list,
        start_date: datetime,
        end_date: datetime,
    ) -> list[dict[str, Any]]:
        """Merge separate query results into unified daily data."""
        # Create lookup dicts
        ideas_map = {str(row.date): row.count for row in ideas}
        votes_map = {str(row.date): row.count for row in votes}
        comments_map = {str(row.date): row.count for row in comments}
        users_map = {str(row.date): row.count for row in users}

        # Generate all dates in range
        result: list[dict[str, Any]] = []
        current = start_date.date()
        end = end_date.date()

        while current <= end:
            date_str = str(current)
            result.append(
                {
                    "period": date_str,
                    "ideas": ideas_map.get(date_str, 0),
                    "votes": votes_map.get(date_str, 0),
                    "comments": comments_map.get(date_str, 0),
                    "users": users_map.get(date_str, 0),
                }
            )
            current += timedelta(days=1)

        return result

    @staticmethod
    def get_weekly_trends(
        db: Session, start_date: datetime, end_date: datetime
    ) -> list[dict[str, Any]]:
        """
        Get weekly aggregated counts for trends chart.

        Uses ISO week numbers, returns list of dicts.
        """
        # Use database-agnostic date formatting (PostgreSQL to_char / SQLite strftime)
        week_expr_idea = _format_week(Idea.created_at)
        week_expr_vote = _format_week(Vote.created_at)
        week_expr_comment = _format_week(Comment.created_at)
        week_expr_user = _format_week(User.created_at)

        ideas_by_week = (
            db.query(
                week_expr_idea.label("week"),
                func.count(Idea.id).label("count"),
            )
            .filter(
                and_(
                    Idea.created_at >= start_date,
                    Idea.created_at <= end_date,
                    Idea.deleted_at.is_(None),
                )
            )
            .group_by(week_expr_idea)
            .all()
        )

        votes_by_week = (
            db.query(
                week_expr_vote.label("week"),
                func.count(Vote.id).label("count"),
            )
            .filter(and_(Vote.created_at >= start_date, Vote.created_at <= end_date))
            .group_by(week_expr_vote)
            .all()
        )

        comments_by_week = (
            db.query(
                week_expr_comment.label("week"),
                func.count(Comment.id).label("count"),
            )
            .filter(
                and_(Comment.created_at >= start_date, Comment.created_at <= end_date)
            )
            .group_by(week_expr_comment)
            .all()
        )

        users_by_week = (
            db.query(
                week_expr_user.label("week"),
                func.count(User.id).label("count"),
            )
            .filter(and_(User.created_at >= start_date, User.created_at <= end_date))
            .group_by(week_expr_user)
            .all()
        )

        return AnalyticsRepository._merge_period_data(
            ideas_by_week, votes_by_week, comments_by_week, users_by_week
        )

    @staticmethod
    def get_monthly_trends(
        db: Session, start_date: datetime, end_date: datetime
    ) -> list[dict[str, Any]]:
        """
        Get monthly aggregated counts for trends chart.

        Returns list of dicts with YYYY-MM format.
        """
        # Use database-agnostic date formatting (PostgreSQL to_char / SQLite strftime)
        month_expr_idea = _format_month(Idea.created_at)
        month_expr_vote = _format_month(Vote.created_at)
        month_expr_comment = _format_month(Comment.created_at)
        month_expr_user = _format_month(User.created_at)

        ideas_by_month = (
            db.query(
                month_expr_idea.label("month"),
                func.count(Idea.id).label("count"),
            )
            .filter(
                and_(
                    Idea.created_at >= start_date,
                    Idea.created_at <= end_date,
                    Idea.deleted_at.is_(None),
                )
            )
            .group_by(month_expr_idea)
            .all()
        )

        votes_by_month = (
            db.query(
                month_expr_vote.label("month"),
                func.count(Vote.id).label("count"),
            )
            .filter(and_(Vote.created_at >= start_date, Vote.created_at <= end_date))
            .group_by(month_expr_vote)
            .all()
        )

        comments_by_month = (
            db.query(
                month_expr_comment.label("month"),
                func.count(Comment.id).label("count"),
            )
            .filter(
                and_(Comment.created_at >= start_date, Comment.created_at <= end_date)
            )
            .group_by(month_expr_comment)
            .all()
        )

        users_by_month = (
            db.query(
                month_expr_user.label("month"),
                func.count(User.id).label("count"),
            )
            .filter(and_(User.created_at >= start_date, User.created_at <= end_date))
            .group_by(month_expr_user)
            .all()
        )

        return AnalyticsRepository._merge_period_data(
            ideas_by_month, votes_by_month, comments_by_month, users_by_month
        )

    @staticmethod
    def _merge_period_data(
        ideas: list, votes: list, comments: list, users: list
    ) -> list[dict[str, Any]]:
        """Merge separate query results into unified period data."""

        # Get period key from either week or month attribute
        def get_period(row) -> str:  # type: ignore[no-untyped-def]
            if hasattr(row, "week"):
                return str(row.week)
            return str(row.month)

        ideas_map = {get_period(row): row.count for row in ideas}
        votes_map = {get_period(row): row.count for row in votes}
        comments_map = {get_period(row): row.count for row in comments}
        users_map = {get_period(row): row.count for row in users}

        # Get all unique periods
        all_periods = sorted(
            set(
                list(ideas_map.keys())
                + list(votes_map.keys())
                + list(comments_map.keys())
                + list(users_map.keys())
            )
        )

        return [
            {
                "period": period,
                "ideas": ideas_map.get(period, 0),
                "votes": votes_map.get(period, 0),
                "comments": comments_map.get(period, 0),
                "users": users_map.get(period, 0),
            }
            for period in all_periods
        ]

    @staticmethod
    def get_category_analytics(db: Session) -> list[dict]:
        """
        Get analytics for all categories.

        Returns list of dicts with category info and metrics.
        """
        # Get all categories with idea counts
        categories = (
            db.query(
                Category.id,
                Category.name_en,
                Category.name_fr,
                func.count(Idea.id).label("total_ideas"),
                func.sum(case((Idea.status == IdeaStatus.APPROVED, 1), else_=0)).label(
                    "approved"
                ),
                func.sum(case((Idea.status == IdeaStatus.PENDING, 1), else_=0)).label(
                    "pending"
                ),
                func.sum(case((Idea.status == IdeaStatus.REJECTED, 1), else_=0)).label(
                    "rejected"
                ),
            )
            .outerjoin(
                Idea, and_(Idea.category_id == Category.id, Idea.deleted_at.is_(None))
            )
            .group_by(Category.id)
            .all()
        )

        result = []
        for cat in categories:
            # Get vote and comment counts for this category
            vote_count = (
                db.query(func.count(Vote.id))
                .join(Idea, Vote.idea_id == Idea.id)
                .filter(and_(Idea.category_id == cat.id, Idea.deleted_at.is_(None)))
                .scalar()
                or 0
            )

            comment_count = (
                db.query(func.count(Comment.id))
                .join(Idea, Comment.idea_id == Idea.id)
                .filter(and_(Idea.category_id == cat.id, Idea.deleted_at.is_(None)))
                .scalar()
                or 0
            )

            # Calculate average score for approved ideas in this category
            avg_score = AnalyticsRepository._calculate_category_avg_score(db, cat.id)

            # Calculate approval rate
            total = int(cat.total_ideas or 0)
            approved = int(cat.approved or 0)
            approval_rate = (approved / total) if total > 0 else 0.0

            result.append(
                {
                    "id": cat.id,
                    "name_en": cat.name_en,
                    "name_fr": cat.name_fr,
                    "total_ideas": total,
                    "approved_ideas": approved,
                    "pending_ideas": int(cat.pending or 0),
                    "rejected_ideas": int(cat.rejected or 0),
                    "total_votes": vote_count,
                    "total_comments": comment_count,
                    "avg_score": round(avg_score, 2),
                    "approval_rate": round(approval_rate, 4),
                }
            )

        return result

    @staticmethod
    def _calculate_category_avg_score(db: Session, category_id: int) -> float:
        """Calculate average vote score for approved ideas in a category."""
        # Get all approved ideas in this category
        ideas_in_category = (
            db.query(Idea.id)
            .filter(
                and_(
                    Idea.category_id == category_id,
                    Idea.status == IdeaStatus.APPROVED,
                    Idea.deleted_at.is_(None),
                )
            )
            .all()
        )

        if not ideas_in_category:
            return 0.0

        idea_ids = [idea.id for idea in ideas_in_category]

        # Calculate scores for all ideas at once
        scores = (
            db.query(
                Vote.idea_id,
                func.sum(
                    case(
                        (Vote.vote_type == VoteType.UPVOTE, 1),
                        (Vote.vote_type == VoteType.DOWNVOTE, -1),
                        else_=0,
                    )
                ).label("score"),
            )
            .filter(Vote.idea_id.in_(idea_ids))
            .group_by(Vote.idea_id)
            .all()
        )

        if not scores:
            return 0.0

        total_score = sum(score.score for score in scores)
        return total_score / len(ideas_in_category)

    @staticmethod
    def get_top_contributors_by_ideas(db: Session, limit: int = 10) -> list[dict]:
        """Get users with most approved ideas."""
        contributors = (
            db.query(
                User.id,
                User.display_name,
                User.username,
                func.count(Idea.id).label("count"),
            )
            .join(Idea, Idea.user_id == User.id)
            .filter(and_(Idea.status == IdeaStatus.APPROVED, Idea.deleted_at.is_(None)))
            .group_by(User.id)
            .order_by(func.count(Idea.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "user_id": c.id,
                "display_name": c.display_name or c.username,
                "username": c.username,
                "count": c.count,
                "rank": idx + 1,
            }
            for idx, c in enumerate(contributors)
        ]

    @staticmethod
    def get_top_contributors_by_votes(db: Session, limit: int = 10) -> list[dict]:
        """Get users who have cast the most votes."""
        contributors = (
            db.query(
                User.id,
                User.display_name,
                User.username,
                func.count(Vote.id).label("count"),
            )
            .join(Vote, Vote.user_id == User.id)
            .group_by(User.id)
            .order_by(func.count(Vote.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "user_id": c.id,
                "display_name": c.display_name or c.username,
                "username": c.username,
                "count": c.count,
                "rank": idx + 1,
            }
            for idx, c in enumerate(contributors)
        ]

    @staticmethod
    def get_top_contributors_by_comments(db: Session, limit: int = 10) -> list[dict]:
        """Get users who have posted the most comments."""
        contributors = (
            db.query(
                User.id,
                User.display_name,
                User.username,
                func.count(Comment.id).label("count"),
            )
            .join(Comment, Comment.user_id == User.id)
            .group_by(User.id)
            .order_by(func.count(Comment.id).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "user_id": c.id,
                "display_name": c.display_name or c.username,
                "username": c.username,
                "count": c.count,
                "rank": idx + 1,
            }
            for idx, c in enumerate(contributors)
        ]

    @staticmethod
    def get_top_contributors_by_score(db: Session, limit: int = 10) -> list[dict]:
        """Get users with highest total vote score on their ideas."""
        # Subquery to calculate score per user
        score_subquery = (
            db.query(
                Idea.user_id,
                func.sum(
                    case(
                        (Vote.vote_type == VoteType.UPVOTE, 1),
                        (Vote.vote_type == VoteType.DOWNVOTE, -1),
                        else_=0,
                    )
                ).label("score"),
            )
            .join(Vote, Vote.idea_id == Idea.id)
            .filter(and_(Idea.status == IdeaStatus.APPROVED, Idea.deleted_at.is_(None)))
            .group_by(Idea.user_id)
            .subquery()
        )

        contributors = (
            db.query(
                User.id,
                User.display_name,
                User.username,
                func.coalesce(score_subquery.c.score, 0).label("count"),
            )
            .outerjoin(score_subquery, score_subquery.c.user_id == User.id)
            .filter(score_subquery.c.score.isnot(None))
            .order_by(score_subquery.c.score.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "user_id": c.id,
                "display_name": c.display_name or c.username,
                "username": c.username,
                "count": int(c.count) if c.count else 0,  # type: ignore[arg-type]
                "rank": idx + 1,
            }
            for idx, c in enumerate(contributors)
        ]

    # ========================================================================
    # Quality Analytics Methods
    # ========================================================================

    @staticmethod
    def count_total_upvotes(db: Session) -> int:
        """Count total upvotes in the system."""
        return (
            db.query(func.count(Vote.id))
            .filter(Vote.vote_type == VoteType.UPVOTE)
            .scalar()
            or 0
        )

    @staticmethod
    def count_votes_with_qualities(db: Session) -> int:
        """Count distinct upvotes that have quality selections."""
        from repositories.db_models import VoteQuality

        return db.query(func.count(func.distinct(VoteQuality.vote_id))).scalar() or 0

    @staticmethod
    def count_votes_with_qualities_upvotes_only(db: Session) -> int:
        """Count distinct upvotes that have quality selections (upvotes only)."""
        from repositories.db_models import VoteQuality

        return (
            db.query(func.count(func.distinct(VoteQuality.vote_id)))
            .join(Vote, VoteQuality.vote_id == Vote.id)
            .filter(Vote.vote_type == VoteType.UPVOTE)
            .scalar()
            or 0
        )

    @staticmethod
    def get_active_qualities(db: Session) -> list:
        """Get all active qualities."""
        from repositories.db_models import Quality

        return db.query(Quality).filter(Quality.is_active.is_(True)).all()

    @staticmethod
    def get_quality_counts_grouped(db: Session) -> list:
        """Get vote count grouped by quality_id."""
        from repositories.db_models import VoteQuality

        return (
            db.query(VoteQuality.quality_id, func.count(VoteQuality.id).label("count"))
            .group_by(VoteQuality.quality_id)
            .all()
        )

    @staticmethod
    def get_top_ideas_for_quality(db: Session, quality_id: int, limit: int = 5) -> list:
        """Get top ideas for a specific quality type."""
        from repositories.db_models import VoteQuality

        return (
            db.query(
                Idea.id, Idea.title, func.count(VoteQuality.id).label("vote_count")
            )
            .join(Vote, Vote.idea_id == Idea.id)
            .join(VoteQuality, VoteQuality.vote_id == Vote.id)
            .filter(VoteQuality.quality_id == quality_id)
            .group_by(Idea.id, Idea.title)
            .order_by(func.count(VoteQuality.id).desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_quality_counts_with_details(db: Session) -> list:
        """Get quality counts with full quality details for officials overview."""
        from repositories.db_models import Quality, VoteQuality

        return (
            db.query(
                Quality.id,
                Quality.key,
                Quality.name_en,
                Quality.name_fr,
                Quality.icon,
                Quality.color,
                func.count(VoteQuality.id).label("count"),
            )
            .outerjoin(VoteQuality, Quality.id == VoteQuality.quality_id)
            .filter(Quality.is_active == True)  # noqa: E712
            .group_by(
                Quality.id,
                Quality.key,
                Quality.name_en,
                Quality.name_fr,
                Quality.icon,
                Quality.color,
            )
            .order_by(Quality.display_order)
            .all()
        )

    @staticmethod
    def get_top_ideas_by_quality_filtered(
        db: Session,
        quality_key: str | None = None,
        limit: int = 10,
    ) -> list:
        """Get top ideas ranked by quality endorsements."""
        from sqlalchemy import desc

        from repositories.db_models import Quality, VoteQuality

        query = (
            db.query(
                Idea.id,
                Idea.title,
                Idea.status,
                Category.name_en.label("category_name_en"),
                Category.name_fr.label("category_name_fr"),
                func.count(VoteQuality.id).label("quality_count"),
            )
            .join(Vote, Vote.idea_id == Idea.id)
            .join(VoteQuality, VoteQuality.vote_id == Vote.id)
            .join(Quality, VoteQuality.quality_id == Quality.id)
            .join(Category, Idea.category_id == Category.id)
            .filter(
                Idea.status == IdeaStatus.APPROVED,
                Vote.vote_type == VoteType.UPVOTE,
            )
        )

        if quality_key:
            query = query.filter(Quality.key == quality_key)

        return (
            query.group_by(
                Idea.id,
                Idea.title,
                Idea.status,
                Category.name_en,
                Category.name_fr,
            )
            .order_by(desc("quality_count"))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_ideas_with_quality_stats(
        db: Session,
        quality_filter: str | None = None,
        min_quality_count: int = 0,
        category_id: int | None = None,
        sort_by: str = "quality_count",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Get ideas with quality statistics for filtering/sorting."""
        from sqlalchemy import desc

        from repositories.db_models import Quality, VoteQuality

        # Quality count subquery
        quality_count_query = (
            db.query(
                Vote.idea_id,
                func.count(func.distinct(VoteQuality.id)).label("quality_count"),
            )
            .join(VoteQuality, VoteQuality.vote_id == Vote.id)
            .filter(Vote.vote_type == VoteType.UPVOTE)
        )
        if quality_filter:
            quality_count_query = quality_count_query.join(
                Quality, VoteQuality.quality_id == Quality.id
            ).filter(Quality.key == quality_filter)
        quality_subquery = quality_count_query.group_by(Vote.idea_id).subquery()

        # Score subquery
        score_subquery = (
            db.query(
                Vote.idea_id,
                func.sum(
                    case(
                        (Vote.vote_type == VoteType.UPVOTE, 1),
                        (Vote.vote_type == VoteType.DOWNVOTE, -1),
                        else_=0,
                    )
                ).label("score"),
            )
            .group_by(Vote.idea_id)
            .subquery()
        )

        query = (
            db.query(
                Idea,
                func.coalesce(quality_subquery.c.quality_count, 0).label(
                    "quality_count"
                ),
                func.coalesce(score_subquery.c.score, 0).label("score"),
            )
            .outerjoin(quality_subquery, Idea.id == quality_subquery.c.idea_id)
            .outerjoin(score_subquery, Idea.id == score_subquery.c.idea_id)
            .filter(Idea.status == IdeaStatus.APPROVED)
        )

        if category_id:
            query = query.filter(Idea.category_id == category_id)

        if min_quality_count > 0:
            query = query.filter(
                func.coalesce(quality_subquery.c.quality_count, 0) >= min_quality_count
            )

        if quality_filter:
            query = query.filter(quality_subquery.c.quality_count > 0)

        total = query.count()

        if sort_by == "quality_count":
            order_col = func.coalesce(quality_subquery.c.quality_count, 0)
        elif sort_by == "score":
            order_col = func.coalesce(score_subquery.c.score, 0)
        else:
            order_col = Idea.created_at  # type: ignore[assignment]

        if sort_order == "desc":
            query = query.order_by(desc(order_col))
        else:
            query = query.order_by(order_col)

        results = query.offset(skip).limit(limit).all()

        return {
            "total": total,
            "items": [
                {
                    "idea": r[0],
                    "quality_count": r[1],
                    "score": r[2],
                }
                for r in results
            ],
        }

    @staticmethod
    def get_idea_with_category_and_author(db: Session, idea_id: int) -> Any | None:
        """Get idea with category and author for detail view."""
        return (
            db.query(Idea, Category, User)
            .join(Category, Idea.category_id == Category.id)
            .join(User, Idea.user_id == User.id)
            .filter(Idea.id == idea_id)
            .first()
        )

    @staticmethod
    def get_vote_counts_for_idea(db: Session, idea_id: int) -> Any:
        """Get upvote and downvote counts for an idea."""
        return (
            db.query(
                func.sum(case((Vote.vote_type == VoteType.UPVOTE, 1), else_=0)).label(
                    "upvotes"
                ),
                func.sum(case((Vote.vote_type == VoteType.DOWNVOTE, 1), else_=0)).label(
                    "downvotes"
                ),
            )
            .filter(Vote.idea_id == idea_id)
            .first()
        )

    @staticmethod
    def get_quality_breakdown_for_idea(db: Session, idea_id: int) -> list:
        """Get quality breakdown for a specific idea."""
        from repositories.db_models import Quality, VoteQuality

        return (
            db.query(
                Quality.key,
                Quality.name_en,
                Quality.name_fr,
                Quality.icon,
                Quality.color,
                func.count(VoteQuality.id).label("count"),
            )
            .join(VoteQuality, VoteQuality.quality_id == Quality.id)
            .join(Vote, Vote.id == VoteQuality.vote_id)
            .filter(Vote.idea_id == idea_id, Vote.vote_type == VoteType.UPVOTE)
            .group_by(
                Quality.key,
                Quality.name_en,
                Quality.name_fr,
                Quality.icon,
                Quality.color,
            )
            .order_by(func.count(VoteQuality.id).desc())
            .all()
        )

    @staticmethod
    def get_top_comments_for_idea(db: Session, idea_id: int, limit: int = 5) -> list:
        """Get top comments by like count for an idea."""
        return (
            db.query(Comment, User)
            .join(User, Comment.user_id == User.id)
            .filter(
                Comment.idea_id == idea_id,
                Comment.deleted_at.is_(None),
                Comment.is_hidden == False,  # noqa: E712
                Comment.like_count > 0,
            )
            .order_by(Comment.like_count.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_quality_breakdowns_batch(db: Session, idea_ids: list[int]) -> list:
        """Get quality breakdown for multiple ideas efficiently."""
        from repositories.db_models import Quality, VoteQuality

        if not idea_ids:
            return []

        return (
            db.query(
                Vote.idea_id,
                Quality.key,
                func.count(VoteQuality.id).label("count"),
            )
            .join(VoteQuality, VoteQuality.vote_id == Vote.id)
            .join(Quality, VoteQuality.quality_id == Quality.id)
            .filter(
                Vote.idea_id.in_(idea_ids),
                Vote.vote_type == VoteType.UPVOTE,
            )
            .group_by(Vote.idea_id, Quality.key)
            .all()
        )

    @staticmethod
    def get_category_quality_breakdown(db: Session) -> list:
        """Get quality distribution per category for officials."""
        from sqlalchemy import desc

        from repositories.db_models import VoteQuality

        return (
            db.query(
                Category.id,
                Category.name_en,
                Category.name_fr,
                func.count(func.distinct(Idea.id)).label("idea_count"),
                func.count(VoteQuality.id).label("quality_count"),
            )
            .join(Idea, Idea.category_id == Category.id)
            .join(Vote, Vote.idea_id == Idea.id)
            .outerjoin(VoteQuality, VoteQuality.vote_id == Vote.id)
            .filter(
                Idea.status == IdeaStatus.APPROVED,
                Vote.vote_type == VoteType.UPVOTE,
            )
            .group_by(Category.id, Category.name_en, Category.name_fr)
            .order_by(desc("quality_count"))
            .all()
        )

    @staticmethod
    def get_quality_time_series(db: Session, days: int = 30) -> list:
        """Get quality voting trends over time."""
        from datetime import timedelta

        from repositories.db_models import VoteQuality

        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        return (
            db.query(
                func.date(VoteQuality.created_at).label("date"),
                func.count(VoteQuality.id).label("count"),
            )
            .filter(VoteQuality.created_at >= start_date)
            .group_by(func.date(VoteQuality.created_at))
            .order_by("date")
            .all()
        )

    # ========================================================================
    # Export Methods
    # ========================================================================

    @staticmethod
    def get_ideas_for_export(
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list:
        """
        Get ideas with vote and comment counts for CSV export.

        Uses subqueries to avoid N+1 query problem.
        """
        # Subqueries for vote counts
        upvote_subq = (
            db.query(
                Vote.idea_id,
                func.count(Vote.id).label("upvotes"),
            )
            .filter(Vote.vote_type == VoteType.UPVOTE)
            .group_by(Vote.idea_id)
            .subquery()
        )

        downvote_subq = (
            db.query(
                Vote.idea_id,
                func.count(Vote.id).label("downvotes"),
            )
            .filter(Vote.vote_type == VoteType.DOWNVOTE)
            .group_by(Vote.idea_id)
            .subquery()
        )

        comment_subq = (
            db.query(
                Comment.idea_id,
                func.count(Comment.id).label("comments"),
            )
            .group_by(Comment.idea_id)
            .subquery()
        )

        # Main query with all data in single query
        query = (
            db.query(
                Idea.id,
                Idea.title,
                Category.name_en.label("category"),
                Idea.status,
                User.username.label("author"),
                Idea.created_at,
                Idea.validated_at,
                func.coalesce(upvote_subq.c.upvotes, 0).label("upvotes"),
                func.coalesce(downvote_subq.c.downvotes, 0).label("downvotes"),
                func.coalesce(comment_subq.c.comments, 0).label("comment_count"),
            )
            .join(Category, Idea.category_id == Category.id)
            .join(User, Idea.user_id == User.id)
            .outerjoin(upvote_subq, Idea.id == upvote_subq.c.idea_id)
            .outerjoin(downvote_subq, Idea.id == downvote_subq.c.idea_id)
            .outerjoin(comment_subq, Idea.id == comment_subq.c.idea_id)
            .filter(Idea.deleted_at.is_(None))
        )

        if start_date:
            query = query.filter(Idea.created_at >= start_date)
        if end_date:
            query = query.filter(Idea.created_at <= end_date)

        return query.order_by(Idea.created_at.desc()).all()

    @staticmethod
    def get_users_for_export(
        db: Session,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list:
        """
        Get users with contribution counts for CSV export.

        Uses subqueries to avoid N+1 query problem.
        """
        # Subqueries for contribution counts
        ideas_subq = (
            db.query(
                Idea.user_id,
                func.count(Idea.id).label("ideas_count"),
            )
            .filter(Idea.deleted_at.is_(None))
            .group_by(Idea.user_id)
            .subquery()
        )

        votes_subq = (
            db.query(
                Vote.user_id,
                func.count(Vote.id).label("votes_count"),
            )
            .group_by(Vote.user_id)
            .subquery()
        )

        comments_subq = (
            db.query(
                Comment.user_id,
                func.count(Comment.id).label("comments_count"),
            )
            .group_by(Comment.user_id)
            .subquery()
        )

        # Main query with all data in single query
        query = (
            db.query(
                User.id,
                User.username,
                User.display_name,
                User.email,
                User.is_active,
                User.is_global_admin,
                User.created_at,
                func.coalesce(ideas_subq.c.ideas_count, 0).label("ideas_count"),
                func.coalesce(votes_subq.c.votes_count, 0).label("votes_count"),
                func.coalesce(comments_subq.c.comments_count, 0).label(
                    "comments_count"
                ),
            )
            .outerjoin(ideas_subq, User.id == ideas_subq.c.user_id)
            .outerjoin(votes_subq, User.id == votes_subq.c.user_id)
            .outerjoin(comments_subq, User.id == comments_subq.c.user_id)
        )

        if start_date:
            query = query.filter(User.created_at >= start_date)
        if end_date:
            query = query.filter(User.created_at <= end_date)

        return query.order_by(User.created_at.desc()).all()
