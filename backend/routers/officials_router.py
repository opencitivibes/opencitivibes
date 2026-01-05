"""
Officials Router - Endpoints for officials analytics dashboard.

All endpoints require official or admin authentication.
Follows the reference pattern from analytics_router.py.
"""

import csv
import io
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

import authentication.auth as auth
import repositories.db_models as db_models
from models.schemas import (
    OfficialsCategoryQualityBreakdown,
    OfficialsIdeaDetail,
    OfficialsIdeaQualityBreakdownItem,
    OfficialsIdeasWithQualityResponse,
    OfficialsIdeaWithQualityStats,
    OfficialsQualityOverview,
    OfficialsTimeSeriesPoint,
    OfficialsTopComment,
    OfficialsTopIdeaByQuality,
)
from repositories.database import get_db
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/officials", tags=["Officials"])

# Export OfficialsTopComment for type checking
__all__ = ["router", "OfficialsTopComment"]


@router.get(
    "/analytics/overview",
    response_model=OfficialsQualityOverview,
    summary="Get quality voting overview statistics",
    description="Returns summary statistics for quality voting. Requires official or admin permissions.",
)
def get_quality_overview(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_official_user),
) -> OfficialsQualityOverview:
    """
    Get quality voting overview statistics.

    Requires official or admin permissions.
    """
    result = AnalyticsService.get_quality_overview_for_officials(db)
    return OfficialsQualityOverview(**result)


@router.get(
    "/analytics/top-ideas",
    response_model=List[OfficialsTopIdeaByQuality],
    summary="Get top ideas by quality endorsements",
    description="Returns top ideas ranked by quality count. Requires official or admin permissions.",
)
def get_top_ideas_by_quality(
    quality_key: Optional[str] = Query(None, description="Filter by quality key"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_official_user),
) -> List[OfficialsTopIdeaByQuality]:
    """
    Get top ideas ranked by quality endorsements.

    Requires official or admin permissions.
    """
    results = AnalyticsService.get_top_ideas_by_quality_for_officials(
        db, quality_key, limit
    )
    return [OfficialsTopIdeaByQuality(**r) for r in results]


@router.get(
    "/analytics/categories",
    response_model=List[OfficialsCategoryQualityBreakdown],
    summary="Get quality distribution by category",
    description="Returns quality count breakdown by category. Requires official or admin permissions.",
)
def get_category_breakdown(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_official_user),
) -> List[OfficialsCategoryQualityBreakdown]:
    """
    Get quality distribution by category.

    Requires official or admin permissions.
    """
    results = AnalyticsService.get_category_quality_breakdown_for_officials(db)
    return [OfficialsCategoryQualityBreakdown(**r) for r in results]


@router.get(
    "/analytics/trends",
    response_model=List[OfficialsTimeSeriesPoint],
    summary="Get quality voting trends over time",
    description="Returns time series data for quality votes. Requires official or admin permissions.",
)
def get_quality_trends(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_official_user),
) -> List[OfficialsTimeSeriesPoint]:
    """
    Get quality voting trends over time.

    Requires official or admin permissions.
    """
    results = AnalyticsService.get_time_series_data_for_officials(db, days)
    return [OfficialsTimeSeriesPoint(**r) for r in results]


@router.get(
    "/ideas",
    response_model=OfficialsIdeasWithQualityResponse,
    summary="Get ideas with quality statistics",
    description="Returns paginated ideas with quality stats and filtering. Requires official or admin permissions.",
)
def get_ideas_with_quality_stats(
    quality_filter: Optional[str] = Query(None, description="Filter by quality key"),
    min_quality_count: int = Query(0, ge=0),
    category_id: Optional[int] = Query(None),
    sort_by: str = Query("quality_count", pattern="^(quality_count|score|created_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_official_user),
) -> OfficialsIdeasWithQualityResponse:
    """
    Get ideas with quality statistics for filtering and sorting.

    Requires official or admin permissions.
    """
    result = AnalyticsService.get_ideas_with_quality_stats_for_officials(
        db,
        quality_filter=quality_filter,
        min_quality_count=min_quality_count,
        category_id=category_id,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )

    return OfficialsIdeasWithQualityResponse(
        total=result["total"],
        items=[
            OfficialsIdeaWithQualityStats(
                id=item["idea"].id,
                title=item["idea"].title,
                description=item["idea"].description,
                category_id=item["idea"].category_id,
                status=item["idea"].status.value,
                created_at=item["idea"].created_at,
                quality_count=item["quality_count"],
                score=item["score"],
            )
            for item in result["items"]
        ],
    )


@router.get(
    "/ideas/{idea_id}",
    response_model=OfficialsIdeaDetail,
    summary="Get single idea with quality breakdown",
    description="Returns detailed idea info with quality breakdown. Requires official or admin permissions.",
)
def get_idea_detail(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_official_user),
) -> OfficialsIdeaDetail:
    """
    Get detailed idea info with quality breakdown for officials.

    Requires official or admin permissions.
    """
    result = AnalyticsService.get_idea_detail_for_officials(db, idea_id)

    return OfficialsIdeaDetail(
        id=result["id"],
        title=result["title"],
        description=result["description"],
        category_id=result["category_id"],
        category_name_en=result["category_name_en"],
        category_name_fr=result["category_name_fr"],
        status=result["status"],
        created_at=result["created_at"],
        score=result["score"],
        upvotes=result["upvotes"],
        downvotes=result["downvotes"],
        quality_count=result["quality_count"],
        quality_breakdown=[
            OfficialsIdeaQualityBreakdownItem(**q) for q in result["quality_breakdown"]
        ],
        author_display_name=result["author_display_name"],
        top_comments=[OfficialsTopComment(**c) for c in result["top_comments"]],
    )


@router.get(
    "/export/ideas.csv",
    summary="Export ideas with quality data as CSV",
    description="Export ideas with quality statistics as CSV file. Requires official or admin permissions.",
)
def export_ideas_csv(
    quality_filter: Optional[str] = Query(None),
    min_quality_count: int = Query(0, ge=0),
    category_id: Optional[int] = Query(None),
    sort_by: str = Query("quality_count", pattern="^(quality_count|score|created_at)$"),
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_official_user),
) -> StreamingResponse:
    """
    Export ideas with quality data as CSV.

    Requires official or admin permissions.
    Rate limited to 10 exports per hour per user.
    """
    # Rate limit check - delegates to service which raises RateLimitExceededException
    from services.rate_limit_service import RateLimitService

    RateLimitService.check_export_rate_limit(current_user.id)

    result = AnalyticsService.get_ideas_with_quality_stats_for_officials(
        db,
        quality_filter=quality_filter,
        min_quality_count=min_quality_count,
        category_id=category_id,
        sort_by=sort_by,
        sort_order="desc",
        skip=0,
        limit=10000,  # Reasonable max for CSV
    )

    # Get quality breakdowns for all ideas
    idea_ids = [item["idea"].id for item in result["items"]]
    quality_breakdowns = AnalyticsService.get_quality_breakdowns_for_ideas(db, idea_ids)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header with quality columns
    writer.writerow(
        [
            "ID",
            "Title",
            "Description",
            "Category ID",
            "Score",
            "Quality Count",
            "Community Benefit",
            "Quality of Life",
            "Urgent",
            "Would Volunteer",
            "Status",
            "Created At",
        ]
    )

    # Data rows
    for item in result["items"]:
        idea = item["idea"]
        description = idea.description[:500] if idea.description else ""
        breakdown = quality_breakdowns.get(idea.id, {})
        writer.writerow(
            [
                idea.id,
                idea.title,
                description,  # Truncate for CSV
                idea.category_id,
                item["score"],
                item["quality_count"],
                breakdown.get("community_benefit", 0),
                breakdown.get("quality_of_life", 0),
                breakdown.get("urgent", 0),
                breakdown.get("would_volunteer", 0),
                idea.status.value,
                idea.created_at.isoformat(),
            ]
        )

    output.seek(0)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"ideas_export_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get(
    "/export/analytics.csv",
    summary="Export quality analytics summary as CSV",
    description="Export quality analytics summary as CSV file. Requires official or admin permissions.",
)
def export_analytics_csv(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_official_user),
) -> StreamingResponse:
    """
    Export quality analytics summary as CSV.

    Requires official or admin permissions.
    Rate limited to 10 exports per hour per user.
    """
    # Rate limit check - delegates to service which raises RateLimitExceededException
    from services.rate_limit_service import RateLimitService

    RateLimitService.check_export_rate_limit(current_user.id)

    overview = AnalyticsService.get_quality_overview_for_officials(db)
    categories = AnalyticsService.get_category_quality_breakdown_for_officials(db)

    output = io.StringIO()
    writer = csv.writer(output)

    # Overview section
    writer.writerow(["=== Quality Overview ==="])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Upvotes", overview["total_upvotes"]])
    writer.writerow(["Votes with Qualities", overview["votes_with_qualities"]])
    writer.writerow(["Adoption Rate", f"{overview['adoption_rate']:.1%}"])
    writer.writerow([])

    # Quality distribution
    writer.writerow(["=== Quality Distribution ==="])
    writer.writerow(["Quality", "Count"])
    for q in overview["quality_distribution"]:
        writer.writerow([q["name_en"], q["count"]])
    writer.writerow([])

    # Category breakdown
    writer.writerow(["=== Category Breakdown ==="])
    writer.writerow(["Category", "Idea Count", "Quality Count"])
    for c in categories:
        writer.writerow([c["name_en"], c["idea_count"], c["quality_count"]])

    output.seek(0)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"analytics_export_{timestamp}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )
