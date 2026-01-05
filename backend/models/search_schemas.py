"""Pydantic schemas for search functionality."""

import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models.schemas import IdeaWithScore


class SearchSortOrder(str, Enum):
    """Sort order for search results."""

    RELEVANCE = "relevance"
    DATE_DESC = "date_desc"
    DATE_ASC = "date_asc"
    SCORE_DESC = "score_desc"
    SCORE_ASC = "score_asc"


class SearchFilters(BaseModel):
    """Filters for search queries."""

    # Existing filters
    category_id: Optional[int] = None
    status: Optional[str] = "APPROVED"  # Default to approved ideas only
    author_id: Optional[int] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    language: Optional[str] = None  # 'en', 'fr', or None for both
    tags: Optional[list[str]] = None  # Filter by tag names

    # Phase 3: Enhanced filters
    category_ids: Optional[list[int]] = None  # Multiple categories (OR logic)
    tag_names: Optional[list[str]] = None  # Filter by tag names (explicit)
    min_score: Optional[int] = None  # Minimum vote score (upvotes - downvotes)
    has_comments: Optional[bool] = None  # Filter ideas with/without comments
    exclude_ids: Optional[list[int]] = None  # Exclude specific idea IDs


class SearchQuery(BaseModel):
    """Search query parameters."""

    q: str = Field(..., min_length=2, max_length=200)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    sort: SearchSortOrder = SearchSortOrder.RELEVANCE
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    highlight: bool = True
    current_user_id: Optional[int] = None  # For user vote status in results

    @field_validator("q")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        """Sanitize search query to prevent FTS injection."""
        # Remove FTS special characters that could cause issues
        # Keep alphanumeric, spaces, and common punctuation
        result = re.sub(r'["\'\*\-\+\(\)\:\^\~\{\}\[\]\\]', " ", v)
        # Normalize whitespace
        return " ".join(result.split())


class SearchHighlight(BaseModel):
    """Highlighted snippets from search results."""

    title: Optional[str] = None
    description: Optional[str] = None


class SearchResultItem(BaseModel):
    """Individual search result with relevance and highlights."""

    idea: IdeaWithScore
    relevance_score: float = Field(ge=0, le=1)
    highlights: Optional[SearchHighlight] = None


class SearchResults(BaseModel):
    """Complete search response."""

    query: str
    total: int
    results: list[SearchResultItem]
    filters_applied: SearchFilters
    search_backend: str

    model_config = {"from_attributes": True}


class SearchSuggestion(BaseModel):
    """Search suggestion/autocomplete item."""

    text: str
    count: int = 0  # Number of matching ideas


# Phase 3: Advanced autocomplete schemas
class TagSuggestion(BaseModel):
    """Tag suggestion with idea count."""

    name: str
    display_name: str
    idea_count: int


class AutocompleteResult(BaseModel):
    """Combined autocomplete response with ideas and tags."""

    ideas: list[str]  # Matching idea titles
    tags: list[TagSuggestion]  # Matching tags with counts
    queries: list[str] = Field(default_factory=list)  # Popular past queries (optional)


class SearchResultsWithTags(BaseModel):
    """Search results with matching tag suggestions."""

    ideas: SearchResults
    matching_tags: list[TagSuggestion] = Field(default_factory=list)
