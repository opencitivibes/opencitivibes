"""
Analytics Router - Admin-only endpoints for dashboard data.

All endpoints require global admin authentication.
Follows the reference pattern from votes_router.py and admin_router.py.
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import authentication.auth as auth
import repositories.db_models as db_models
from models.schemas import (
    CacheRefreshResponse,
    CategoriesAnalyticsResponse,
    ContributorType,
    Granularity,
    OverviewMetrics,
    TopContributorsResponse,
    TrendsResponse,
)
from repositories.database import get_db
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/admin/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=OverviewMetrics,
    summary="Get dashboard overview metrics",
    description="Returns summary counts for users, ideas, votes, and comments. Cached for 10 minutes.",
)
def get_overview(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> OverviewMetrics:
    """
    Get overview metrics for the analytics dashboard.

    Domain exceptions are caught by centralized exception handlers.
    """
    return AnalyticsService.get_overview(db)


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Get time-series trend data",
    description="Returns aggregated counts over time for ideas, votes, comments, and user registrations.",
)
def get_trends(
    start_date: date = Query(
        ...,
        description="Start date for the trend data (YYYY-MM-DD)",
        examples=["2025-01-01"],
    ),
    end_date: date = Query(
        ...,
        description="End date for the trend data (YYYY-MM-DD)",
        examples=["2025-12-31"],
    ),
    granularity: Granularity = Query(
        Granularity.WEEK,
        description="Time granularity: day, week, or month",
    ),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> TrendsResponse:
    """
    Get time-series trend data for the specified date range.

    Domain exceptions are caught by centralized exception handlers.
    """
    # Convert date to datetime for service
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    return AnalyticsService.get_trends(
        db,
        start_date=start_datetime,
        end_date=end_datetime,
        granularity=granularity,
    )


@router.get(
    "/categories",
    response_model=CategoriesAnalyticsResponse,
    summary="Get category performance analytics",
    description="Returns analytics for all categories including idea counts, approval rates, and engagement metrics.",
)
def get_categories_analytics(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> CategoriesAnalyticsResponse:
    """
    Get analytics breakdown by category.

    Domain exceptions are caught by centralized exception handlers.
    """
    return AnalyticsService.get_categories_analytics(db)


@router.get(
    "/top-contributors",
    response_model=TopContributorsResponse,
    summary="Get top contributors",
    description="Returns ranked list of top contributors by the specified metric.",
)
def get_top_contributors(
    contributor_type: ContributorType = Query(
        ContributorType.IDEAS,
        alias="type",
        description="Type of ranking: ideas, votes, comments, or score",
    ),
    limit: int = Query(
        10,
        ge=5,
        le=50,
        description="Number of contributors to return (5-50)",
    ),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> TopContributorsResponse:
    """
    Get top contributors by the specified metric.

    Domain exceptions are caught by centralized exception handlers.
    """
    return AnalyticsService.get_top_contributors(
        db,
        contributor_type=contributor_type,
        limit=limit,
    )


@router.post(
    "/refresh",
    response_model=CacheRefreshResponse,
    summary="Refresh analytics cache",
    description="Invalidates the analytics cache, forcing fresh data on next request.",
)
def refresh_cache(
    cache_key: Optional[str] = Query(
        None,
        description="Specific cache key to invalidate, or None for all",
    ),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> CacheRefreshResponse:
    """
    Manually refresh the analytics cache.

    Domain exceptions are caught by centralized exception handlers.
    """
    AnalyticsService.invalidate_cache(cache_key)
    return CacheRefreshResponse(
        message="Cache invalidated successfully",
        key=cache_key or "all",
    )


@router.get(
    "/export",
    summary="Export analytics data",
    description="Export analytics data as CSV file.",
)
def export_data(
    data_type: str = Query(
        "overview",
        description="Type of data to export: overview, ideas, users, categories",
        pattern="^(overview|ideas|users|categories)$",
    ),
    start_date: Optional[date] = Query(
        None,
        description="Start date for filtering (YYYY-MM-DD)",
    ),
    end_date: Optional[date] = Query(
        None,
        description="End date for filtering (YYYY-MM-DD)",
    ),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> StreamingResponse:
    """
    Export analytics data as a CSV file.

    Domain exceptions are caught by centralized exception handlers.
    """
    from services.analytics_export_service import AnalyticsExportService

    # Convert dates to datetime if provided
    start_datetime = (
        datetime.combine(start_date, datetime.min.time()) if start_date else None
    )
    end_datetime = datetime.combine(end_date, datetime.max.time()) if end_date else None

    # Generate CSV content
    csv_content = AnalyticsExportService.generate_csv(
        db,
        data_type=data_type,
        start_date=start_datetime,
        end_date=end_datetime,
    )

    # Create filename using timezone-aware datetime
    from datetime import timezone as tz

    timestamp = datetime.now(tz.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{data_type}_export_{timestamp}.csv"

    # Return as streaming response
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


@router.get(
    "/qualities",
    summary="Get vote quality analytics",
    description="Returns analytics on quality voting patterns, adoption rates, and top ideas by quality.",
)
def get_quality_analytics(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
):
    """
    Get analytics for vote qualities.

    Returns:
    - Total upvotes and votes with quality selections
    - Adoption rate (% of upvotes that include qualities)
    - Distribution of quality selections
    - Top 5 ideas for each quality type

    Domain exceptions are caught by centralized exception handlers.
    """

    result = AnalyticsService.get_quality_analytics(db)
    return result
