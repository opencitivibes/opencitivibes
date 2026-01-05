"""
Analytics Service - Business logic for dashboard analytics.

Implements caching to reduce database load on frequently accessed metrics.
Cache TTL is 10 minutes for overview data, 15 minutes for trends.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from models.exceptions import ValidationException
from models.schemas import (
    CategoriesAnalyticsResponse,
    CategoryAnalytics,
    ContributorType,
    Granularity,
    OverviewMetrics,
    QualityAnalyticsResponse,
    QualityDistribution,
    QualityTopIdeas,
    TopContributor,
    TopContributorsResponse,
    TopIdeaByQuality,
    TrendDataPoint,
    TrendsResponse,
)
from repositories.analytics_repository import AnalyticsRepository


class AnalyticsService:
    """Service for analytics dashboard data."""

    # Cache storage: {cache_key: (data, timestamp)}
    _cache: dict[str, tuple[Any, float]] = {}
    _overview_ttl: float = 600.0  # 10 minutes in seconds
    _trends_ttl: float = 900.0  # 15 minutes in seconds
    _categories_ttl: float = 600.0  # 10 minutes in seconds
    _contributors_ttl: float = 900.0  # 15 minutes in seconds

    @classmethod
    def _get_from_cache(cls, key: str, ttl: float) -> Any | None:
        """
        Get data from cache if not expired.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            Cached data or None if expired/missing
        """
        if key not in cls._cache:
            return None

        data, cached_time = cls._cache[key]
        if time.time() - cached_time > ttl:
            # Cache expired
            del cls._cache[key]
            return None

        return data

    @classmethod
    def _set_cache(cls, key: str, data: Any) -> None:
        """
        Store data in cache.

        Args:
            key: Cache key
            data: Data to cache
        """
        cls._cache[key] = (data, time.time())

    @classmethod
    def invalidate_cache(cls, key: str | None = None) -> None:
        """
        Invalidate cache.

        Args:
            key: Specific cache key to invalidate, or None for all.
        """
        if key:
            cls._cache.pop(key, None)
        else:
            cls._cache.clear()

    @staticmethod
    def get_overview(db: Session) -> OverviewMetrics:
        """
        Get overview metrics for dashboard.

        Cached for 10 minutes to reduce database load.

        Args:
            db: Database session

        Returns:
            OverviewMetrics with all dashboard summary data
        """
        cache_key = "overview"

        cached_data = AnalyticsService._get_from_cache(
            cache_key, AnalyticsService._overview_ttl
        )
        if cached_data is not None:
            return OverviewMetrics(**cached_data)

        # Fetch from repository
        overview = AnalyticsRepository.get_overview_counts(db)
        week_counts = AnalyticsRepository.get_this_week_counts(db)

        metrics = {
            **overview,
            **week_counts,
            "generated_at": datetime.now(timezone.utc),
        }

        AnalyticsService._set_cache(cache_key, metrics)
        return OverviewMetrics(**metrics)

    @staticmethod
    def get_trends(
        db: Session,
        start_date: datetime,
        end_date: datetime,
        granularity: Granularity = Granularity.WEEK,
    ) -> TrendsResponse:
        """
        Get time-series trend data.

        Args:
            db: Database session
            start_date: Start of date range
            end_date: End of date range
            granularity: Day, Week, or Month aggregation

        Returns:
            TrendsResponse with time-series data

        Raises:
            ValidationException: If date range is invalid
        """
        # Validate date range
        if start_date > end_date:
            raise ValidationException("Start date must be before end date")

        max_range = timedelta(days=365 * 2)  # 2 years max
        if end_date - start_date > max_range:
            raise ValidationException("Date range cannot exceed 2 years")

        # Cache key includes parameters
        cache_key = f"trends_{start_date.date()}_{end_date.date()}_{granularity.value}"

        cached_data = AnalyticsService._get_from_cache(
            cache_key, AnalyticsService._trends_ttl
        )
        if cached_data is not None:
            return TrendsResponse(
                granularity=Granularity(cached_data["granularity"]),
                start_date=datetime.fromisoformat(cached_data["start_date"]),
                end_date=datetime.fromisoformat(cached_data["end_date"]),
                data=[TrendDataPoint(**d) for d in cached_data["data"]],
            )

        # Fetch based on granularity
        if granularity == Granularity.DAY:
            data = AnalyticsRepository.get_daily_trends(db, start_date, end_date)
        elif granularity == Granularity.WEEK:
            data = AnalyticsRepository.get_weekly_trends(db, start_date, end_date)
        else:  # MONTH
            data = AnalyticsRepository.get_monthly_trends(db, start_date, end_date)

        response = TrendsResponse(
            granularity=granularity,
            start_date=start_date,
            end_date=end_date,
            data=[TrendDataPoint(**d) for d in data],
        )

        # Cache the dict version for serialization
        AnalyticsService._set_cache(
            cache_key,
            {
                "granularity": granularity.value,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "data": data,
            },
        )

        return response

    @staticmethod
    def get_categories_analytics(db: Session) -> CategoriesAnalyticsResponse:
        """
        Get analytics for all categories.

        Cached for 10 minutes.

        Args:
            db: Database session

        Returns:
            CategoriesAnalyticsResponse with category metrics
        """
        cache_key = "categories_analytics"

        cached_data = AnalyticsService._get_from_cache(
            cache_key, AnalyticsService._categories_ttl
        )
        if cached_data is not None:
            return CategoriesAnalyticsResponse(
                categories=[CategoryAnalytics(**c) for c in cached_data["categories"]],
                generated_at=datetime.fromisoformat(cached_data["generated_at"]),
            )

        categories_data = AnalyticsRepository.get_category_analytics(db)
        generated_at = datetime.now(timezone.utc)

        response = CategoriesAnalyticsResponse(
            categories=[CategoryAnalytics(**c) for c in categories_data],
            generated_at=generated_at,
        )

        AnalyticsService._set_cache(
            cache_key,
            {
                "categories": categories_data,
                "generated_at": generated_at.isoformat(),
            },
        )

        return response

    @staticmethod
    def get_top_contributors(
        db: Session,
        contributor_type: ContributorType = ContributorType.IDEAS,
        limit: int = 10,
    ) -> TopContributorsResponse:
        """
        Get top contributors by type.

        Args:
            db: Database session
            contributor_type: Type of ranking (ideas, votes, comments, score)
            limit: Number of results (5-50)

        Returns:
            TopContributorsResponse with contributor rankings

        Raises:
            ValidationException: If limit is out of range
        """
        if not 5 <= limit <= 50:
            raise ValidationException("Limit must be between 5 and 50")

        cache_key = f"contributors_{contributor_type.value}_{limit}"

        cached_data = AnalyticsService._get_from_cache(
            cache_key, AnalyticsService._contributors_ttl
        )
        if cached_data is not None:
            return TopContributorsResponse(
                type=ContributorType(cached_data["type"]),
                contributors=[TopContributor(**c) for c in cached_data["contributors"]],
                generated_at=datetime.fromisoformat(cached_data["generated_at"]),
            )

        # Fetch based on type
        if contributor_type == ContributorType.IDEAS:
            contributors_data = AnalyticsRepository.get_top_contributors_by_ideas(
                db, limit
            )
        elif contributor_type == ContributorType.VOTES:
            contributors_data = AnalyticsRepository.get_top_contributors_by_votes(
                db, limit
            )
        elif contributor_type == ContributorType.COMMENTS:
            contributors_data = AnalyticsRepository.get_top_contributors_by_comments(
                db, limit
            )
        else:  # SCORE
            contributors_data = AnalyticsRepository.get_top_contributors_by_score(
                db, limit
            )

        generated_at = datetime.now(timezone.utc)
        response = TopContributorsResponse(
            type=contributor_type,
            contributors=[TopContributor(**c) for c in contributors_data],
            generated_at=generated_at,
        )

        AnalyticsService._set_cache(
            cache_key,
            {
                "type": contributor_type.value,
                "contributors": contributors_data,
                "generated_at": generated_at.isoformat(),
            },
        )

        return response

    @staticmethod
    def get_quality_analytics(db: Session) -> "QualityAnalyticsResponse":
        """
        Get analytics for vote qualities.

        Cached for 10 minutes.

        Args:
            db: Database session

        Returns:
            QualityAnalyticsResponse with quality metrics
        """
        cache_key = "quality_analytics"

        cached_data = AnalyticsService._get_from_cache(
            cache_key, AnalyticsService._overview_ttl
        )
        if cached_data is not None:
            return QualityAnalyticsResponse(
                total_upvotes=cached_data["total_upvotes"],
                votes_with_qualities=cached_data["votes_with_qualities"],
                adoption_rate=cached_data["adoption_rate"],
                distribution=[
                    QualityDistribution(**d) for d in cached_data["distribution"]
                ],
                top_ideas_by_quality=[
                    QualityTopIdeas(
                        quality_key=t["quality_key"],
                        quality_name_en=t["quality_name_en"],
                        quality_name_fr=t["quality_name_fr"],
                        icon=t.get("icon"),
                        color=t.get("color"),
                        ideas=[TopIdeaByQuality(**i) for i in t["ideas"]],
                    )
                    for t in cached_data["top_ideas_by_quality"]
                ],
                generated_at=datetime.fromisoformat(cached_data["generated_at"]),
            )

        # Use repository methods
        total_upvotes = AnalyticsRepository.count_total_upvotes(db)
        votes_with_qualities = AnalyticsRepository.count_votes_with_qualities(db)

        # Adoption rate
        adoption_rate = (
            (votes_with_qualities / total_upvotes * 100) if total_upvotes > 0 else 0
        )

        # Get all qualities for reference
        qualities = AnalyticsRepository.get_active_qualities(db)
        quality_map = {q.id: q for q in qualities}

        # Count by quality type
        quality_counts = AnalyticsRepository.get_quality_counts_grouped(db)

        # Calculate total for percentages
        total_quality_selections = sum(count for _, count in quality_counts)

        distribution = []
        for quality_id, count in quality_counts:
            quality = quality_map.get(quality_id)
            if quality:
                distribution.append(
                    QualityDistribution(
                        quality_key=quality.key,
                        quality_name_en=quality.name_en,
                        quality_name_fr=quality.name_fr,
                        icon=quality.icon,
                        color=quality.color,
                        count=count,
                        percentage=(
                            count / total_quality_selections * 100
                            if total_quality_selections > 0
                            else 0
                        ),
                    )
                )

        # Sort by count descending
        distribution.sort(key=lambda x: x.count, reverse=True)

        # Top ideas by each quality
        top_ideas_by_quality = []
        for quality in qualities:
            top_ideas = AnalyticsRepository.get_top_ideas_for_quality(db, quality.id)

            if top_ideas:
                top_ideas_by_quality.append(
                    QualityTopIdeas(
                        quality_key=quality.key,
                        quality_name_en=quality.name_en,
                        quality_name_fr=quality.name_fr,
                        icon=quality.icon,
                        color=quality.color,
                        ideas=[
                            TopIdeaByQuality(id=i.id, title=i.title, count=i.vote_count)
                            for i in top_ideas
                        ],
                    )
                )

        generated_at = datetime.now(timezone.utc)

        response = QualityAnalyticsResponse(
            total_upvotes=total_upvotes,
            votes_with_qualities=votes_with_qualities,
            adoption_rate=round(adoption_rate, 1),
            distribution=distribution,
            top_ideas_by_quality=top_ideas_by_quality,
            generated_at=generated_at,
        )

        # Cache the data
        AnalyticsService._set_cache(
            cache_key,
            {
                "total_upvotes": total_upvotes,
                "votes_with_qualities": votes_with_qualities,
                "adoption_rate": round(adoption_rate, 1),
                "distribution": [
                    {
                        "quality_key": d.quality_key,
                        "quality_name_en": d.quality_name_en,
                        "quality_name_fr": d.quality_name_fr,
                        "icon": d.icon,
                        "color": d.color,
                        "count": d.count,
                        "percentage": d.percentage,
                    }
                    for d in distribution
                ],
                "top_ideas_by_quality": [
                    {
                        "quality_key": t.quality_key,
                        "quality_name_en": t.quality_name_en,
                        "quality_name_fr": t.quality_name_fr,
                        "icon": t.icon,
                        "color": t.color,
                        "ideas": [
                            {"id": i.id, "title": i.title, "count": i.count}
                            for i in t.ideas
                        ],
                    }
                    for t in top_ideas_by_quality
                ],
                "generated_at": generated_at.isoformat(),
            },
        )

        return response

    # ========================================================================
    # Officials Analytics Methods
    # ========================================================================

    @staticmethod
    def get_quality_overview_for_officials(db: Session) -> dict[str, Any]:
        """
        Get overview of quality voting statistics for officials dashboard.

        Returns:
            - total_upvotes: Total upvotes in system
            - votes_with_qualities: Upvotes that have quality selections
            - adoption_rate: Percentage of upvotes with qualities
            - quality_distribution: Count per quality type
        """
        total_upvotes = AnalyticsRepository.count_total_upvotes(db)
        votes_with_qualities = (
            AnalyticsRepository.count_votes_with_qualities_upvotes_only(db)
        )
        quality_counts = AnalyticsRepository.get_quality_counts_with_details(db)

        return {
            "total_upvotes": total_upvotes,
            "votes_with_qualities": votes_with_qualities,
            "adoption_rate": (
                votes_with_qualities / total_upvotes if total_upvotes > 0 else 0.0
            ),
            "quality_distribution": [
                {
                    "quality_id": q.id,
                    "key": q.key,
                    "name_en": q.name_en,
                    "name_fr": q.name_fr,
                    "icon": q.icon,
                    "color": q.color,
                    "count": q.count or 0,
                }
                for q in quality_counts
            ],
        }

    @staticmethod
    def get_top_ideas_by_quality_for_officials(
        db: Session,
        quality_key: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get top ideas ranked by quality endorsements for officials.

        Args:
            quality_key: Filter by specific quality (or all if None)
            limit: Max number of ideas to return
        """
        results = AnalyticsRepository.get_top_ideas_by_quality_filtered(
            db, quality_key, limit
        )

        return [
            {
                "idea_id": r.id,
                "title": r.title,
                "category_name_en": r.category_name_en,
                "category_name_fr": r.category_name_fr,
                "quality_count": r.quality_count,
            }
            for r in results
        ]

    @staticmethod
    def get_ideas_with_quality_stats_for_officials(
        db: Session,
        quality_filter: str | None = None,
        min_quality_count: int = 0,
        category_id: int | None = None,
        sort_by: str = "quality_count",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get ideas with quality statistics for filtering/sorting.

        Args:
            quality_filter: Filter by quality key
            min_quality_count: Minimum quality count
            category_id: Filter by category
            sort_by: Sort by quality_count, score, or created_at
            sort_order: asc or desc
            skip: Pagination offset
            limit: Page size
        """
        return AnalyticsRepository.get_ideas_with_quality_stats(
            db,
            quality_filter=quality_filter,
            min_quality_count=min_quality_count,
            category_id=category_id,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_idea_detail_for_officials(
        db: Session,
        idea_id: int,
    ) -> dict[str, Any]:
        """
        Get detailed idea info with quality breakdown for officials.

        Args:
            idea_id: The idea ID

        Returns:
            Dictionary with idea details and quality breakdown

        Raises:
            NotFoundException: If idea not found
        """
        from models.exceptions import NotFoundException

        # Get idea with category and author
        idea = AnalyticsRepository.get_idea_with_category_and_author(db, idea_id)

        if not idea:
            raise NotFoundException("Idea not found")

        idea_obj, category, author = idea

        # Get vote counts
        vote_counts = AnalyticsRepository.get_vote_counts_for_idea(db, idea_id)

        upvotes = vote_counts[0] or 0 if vote_counts else 0
        downvotes = vote_counts[1] or 0 if vote_counts else 0

        # Get quality breakdown
        quality_breakdown = AnalyticsRepository.get_quality_breakdown_for_idea(
            db, idea_id
        )

        total_quality_count = sum(q[5] for q in quality_breakdown)

        # Get top comments by like count (max 5)
        top_comments_query = AnalyticsRepository.get_top_comments_for_idea(db, idea_id)

        top_comments = [
            {
                "id": comment.id,
                "content": comment.content,
                "author_display_name": comment_author.display_name
                or comment_author.username,
                "like_count": comment.like_count,
                "created_at": comment.created_at,
            }
            for comment, comment_author in top_comments_query
        ]

        return {
            "id": idea_obj.id,
            "title": idea_obj.title,
            "description": idea_obj.description,
            "category_id": idea_obj.category_id,
            "category_name_en": category.name_en,
            "category_name_fr": category.name_fr,
            "status": idea_obj.status.value,
            "created_at": idea_obj.created_at,
            "score": upvotes - downvotes,
            "upvotes": upvotes,
            "downvotes": downvotes,
            "quality_count": total_quality_count,
            "quality_breakdown": [
                {
                    "quality_key": q[0],
                    "quality_name_en": q[1],
                    "quality_name_fr": q[2],
                    "icon": q[3],
                    "color": q[4],
                    "count": q[5],
                }
                for q in quality_breakdown
            ],
            "author_display_name": author.display_name or author.username,
            "top_comments": top_comments,
        }

    @staticmethod
    def get_quality_breakdowns_for_ideas(
        db: Session,
        idea_ids: list[int],
    ) -> dict[int, dict[str, int]]:
        """
        Get quality breakdown for multiple ideas efficiently.

        Args:
            idea_ids: List of idea IDs

        Returns:
            Dict mapping idea_id -> {quality_key: count}
        """
        if not idea_ids:
            return {}

        results = AnalyticsRepository.get_quality_breakdowns_batch(db, idea_ids)

        # Build the result dict
        breakdowns: dict[int, dict[str, int]] = {idea_id: {} for idea_id in idea_ids}
        for idea_id, quality_key, count in results:
            breakdowns[idea_id][quality_key] = count

        return breakdowns

    @staticmethod
    def get_category_quality_breakdown_for_officials(
        db: Session,
    ) -> list[dict[str, Any]]:
        """Get quality distribution per category for officials."""
        results = AnalyticsRepository.get_category_quality_breakdown(db)

        return [
            {
                "category_id": r.id,
                "name_en": r.name_en,
                "name_fr": r.name_fr,
                "idea_count": r.idea_count,
                "quality_count": r.quality_count,
            }
            for r in results
        ]

    @staticmethod
    def get_time_series_data_for_officials(
        db: Session,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get quality voting trends over time for officials."""
        results = AnalyticsRepository.get_quality_time_series(db, days)

        return [{"date": str(r.date), "count": r.count} for r in results]
