"""
Standardized pagination parameters for consistent API pagination.
"""

from fastapi import Query
from typing import Annotated

# Standard pagination for most list endpoints
PaginationSkip = Annotated[int, Query(ge=0, description="Number of records to skip")]
PaginationLimit = Annotated[
    int, Query(ge=1, le=100, description="Maximum number of records to return")
]

# Pagination for endpoints with larger datasets (admin panels)
PaginationLimitLarge = Annotated[
    int, Query(ge=1, le=200, description="Maximum number of records to return")
]

# Pagination for comments (many per idea)
PaginationLimitComments = Annotated[
    int, Query(ge=1, le=100, description="Maximum number of comments to return")
]

# Pagination for recommendation lists (similar ideas)
PaginationLimitSmall = Annotated[
    int, Query(ge=1, le=10, description="Maximum number of recommendations to return")
]


def get_pagination_params(
    skip: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)
) -> tuple[int, int]:
    """
    Standard pagination parameters.

    Args:
        skip: Number of records to skip (default 0)
        limit: Maximum number of records to return (default 20, max 100)

    Returns:
        Tuple of (skip, limit)
    """
    return skip, limit


def get_pagination_params_large(
    skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200)
) -> tuple[int, int]:
    """
    Pagination parameters for large datasets.

    Args:
        skip: Number of records to skip (default 0)
        limit: Maximum number of records to return (default 50, max 200)

    Returns:
        Tuple of (skip, limit)
    """
    return skip, limit
