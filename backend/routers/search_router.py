"""Search API endpoints."""

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

import authentication.auth as auth
from helpers.language import parse_accept_language
import repositories.db_models as db_models
from helpers.pagination import PaginationLimit, PaginationSkip
from models.schemas import SearchBackendInfo, SearchHealthStatus
from models.search_schemas import SearchResults, SearchSortOrder
from repositories.database import get_db
from services.search import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/ideas", response_model=SearchResults)
def search_ideas(
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    status: Optional[str] = Query("APPROVED", description="Filter by status"),
    author_id: Optional[int] = Query(None, description="Filter by author"),
    from_date: Optional[datetime] = Query(None, description="Filter by start date"),
    to_date: Optional[datetime] = Query(None, description="Filter by end date"),
    language: Optional[str] = Query(
        None, pattern="^(en|fr)$", description="Filter by language (filter)"
    ),
    sort: SearchSortOrder = Query(SearchSortOrder.RELEVANCE, description="Sort order"),
    skip: PaginationSkip = 0,
    limit: PaginationLimit = 20,
    highlight: bool = Query(True, description="Include highlighted snippets"),
    # Phase 3: Enhanced filters
    category_ids: Optional[list[int]] = Query(
        None, description="Filter by multiple categories"
    ),
    tag_names: Optional[list[str]] = Query(None, description="Filter by tag names"),
    min_score: Optional[int] = Query(None, description="Minimum vote score"),
    has_comments: Optional[bool] = Query(
        None, description="Filter ideas with/without comments"
    ),
    exclude_ids: Optional[list[int]] = Query(
        None, description="Exclude specific idea IDs"
    ),
    accept_language: Annotated[str, Header(alias="Accept-Language")] = "fr",
    db: Session = Depends(get_db),
    current_user: Optional[db_models.User] = Depends(auth.get_current_user_optional),
) -> SearchResults:
    """
    Search ideas using full-text search.

    Returns ideas matching the search query with relevance scores
    and optional highlighted snippets.

    Phase 3 enhanced filters:
    - category_ids: Filter by multiple categories (OR logic)
    - tag_names: Filter by specific tags
    - min_score: Minimum vote score (upvotes - downvotes)
    - has_comments: Filter ideas with/without comments
    - exclude_ids: Exclude specific idea IDs from results

    Domain exceptions are caught by centralized exception handlers.

    Language prioritization: If Accept-Language header is provided, results
    within the same relevance tier will show preferred language first.
    """
    user_id: int | None = current_user.id if current_user else None  # type: ignore[assignment]
    preferred_lang = parse_accept_language(accept_language)
    return SearchService.search_ideas(
        db=db,
        query=q,
        category_id=category_id,
        status=status,
        author_id=author_id,
        from_date=from_date,
        to_date=to_date,
        language=language,
        sort=sort,
        skip=skip,
        limit=limit,
        highlight=highlight,
        current_user_id=user_id,
        category_ids=category_ids,
        tag_names=tag_names,
        min_score=min_score,
        has_comments=has_comments,
        exclude_ids=exclude_ids,
        preferred_language=preferred_lang,
    )


@router.get("/suggestions", response_model=list[str])
def get_suggestions(
    q: str = Query(..., min_length=2, max_length=100, description="Partial query"),
    limit: int = Query(5, ge=1, le=10, description="Max suggestions"),
    db: Session = Depends(get_db),
) -> list[str]:
    """
    Get search suggestions for autocomplete.

    Returns a list of suggested search terms based on partial input.
    """
    return SearchService.get_suggestions(db, q, limit)


@router.get("/info", response_model=SearchBackendInfo)
def get_search_info(
    db: Session = Depends(get_db),
) -> SearchBackendInfo:
    """
    Get information about the search backend.

    Returns the current backend type and availability status.
    """

    return SearchService.get_backend_info(db)


@router.get("/health", response_model=SearchHealthStatus)
def search_health_check(
    db: Session = Depends(get_db),
) -> SearchHealthStatus:
    """
    Check search backend health and index status.

    Returns detailed health information including:
    - Backend availability status
    - Number of indexed ideas
    - Index coverage percentage
    """

    return SearchService.get_health_status(db)


@router.post("/reindex/{idea_id}", status_code=204)
def reindex_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> None:
    """
    Reindex a single idea.

    Admin-only operation.
    """
    SearchService.reindex_idea(db, idea_id)


@router.post("/rebuild", status_code=200)
def rebuild_index(
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(auth.get_admin_user),
) -> dict:
    """
    Rebuild the entire search index.

    Admin-only operation. Returns the number of ideas indexed.
    """
    count = SearchService.rebuild_index(db)
    return {"indexed": count}


# Phase 3: New endpoints


@router.get("/autocomplete")
def autocomplete(
    q: str = Query(..., min_length=2, max_length=100, description="Partial query"),
    limit: int = Query(5, ge=1, le=10, description="Max suggestions per type"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Get combined autocomplete suggestions for ideas and tags (Phase 3).

    Returns:
    - ideas: List of matching idea titles
    - tags: List of matching tags with idea counts
    - queries: List of popular past queries (optional)
    """
    return SearchService.get_autocomplete(db, q, limit)


@router.get("/with-tags")
def search_with_tags(
    q: str = Query(..., min_length=2, max_length=200, description="Search query"),
    skip: PaginationSkip = 0,
    limit: PaginationLimit = 20,
    db: Session = Depends(get_db),
    current_user: Optional[db_models.User] = Depends(auth.get_current_user_optional),
) -> dict:
    """
    Search ideas and return matching tags alongside results (Phase 3).

    If query starts with '#', searches tags only.

    Returns:
    - ideas: SearchResults object
    - matching_tags: List of matching tags with idea counts
    """
    user_id: int | None = current_user.id if current_user else None  # type: ignore[assignment]
    return SearchService.search_with_tags(
        db=db,
        query=q,
        skip=skip,
        limit=limit,
        current_user_id=user_id,
    )
