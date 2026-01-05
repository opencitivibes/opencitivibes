from enum import Enum

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from repositories.db_models import (
    AppealStatus,
    ContentType,
    FlagReason,
    FlagStatus,
    IdeaStatus,
    PenaltyStatus,
    PenaltyType,
    VoteType,
)


# Comment Sort Order Enum (used by routers and services)
class CommentSortOrder(str, Enum):
    """Comment sorting options."""

    RELEVANCE = "relevance"  # likes + recency
    NEWEST = "newest"
    OLDEST = "oldest"
    MOST_LIKED = "most_liked"


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    display_name: str


class UserCreate(UserBase):
    password: str
    requests_official_status: Optional[bool] = False
    official_title_request: Optional[str] = None
    # Consent fields (required for Law 25 compliance)
    accepts_terms: bool = Field(..., description="User must accept Terms of Service")
    accepts_privacy_policy: bool = Field(
        ..., description="User must accept Privacy Policy"
    )
    marketing_consent: bool = Field(
        default=False, description="Optional: User opts into marketing communications"
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class User(UserBase):
    id: int
    avatar_url: Optional[str] = None
    is_global_admin: bool
    is_active: bool
    is_official: bool = False
    official_title: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# User Profile Management Schemas
class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserActivityHistory(BaseModel):
    ideas_count: int
    approved_ideas_count: int
    pending_ideas_count: int
    rejected_ideas_count: int
    votes_count: int
    comments_count: int
    recent_ideas: List["IdeaWithScore"]
    recent_comments: List["Comment"]


# User Management Schemas (Admin)
class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_global_admin: Optional[bool] = None


class UserList(BaseModel):
    id: int
    email: EmailStr
    username: str
    display_name: str
    is_active: bool
    is_global_admin: bool
    is_official: bool = False
    official_title: Optional[str] = None
    has_category_admin_role: bool = False
    created_at: datetime
    # Reputation fields for admin badges
    trust_score: int = 50  # 0-100, default 50
    vote_score: int = 0  # upvotes - downvotes received
    penalty_count: int = 0  # total penalties
    active_penalty_count: int = 0  # currently active penalties

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Paginated user list response with total count."""

    users: List["UserList"]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserPublic(BaseModel):
    """Public user profile (visible to others)."""

    id: int
    username: str
    display_name: str
    avatar_url: Optional[str] = None
    is_official: bool = False
    official_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Official Role Schemas
# ============================================================================


class OfficialInfo(BaseModel):
    """Public official information."""

    is_official: bool
    official_title: Optional[str] = None
    official_verified_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OfficialGrant(BaseModel):
    """Request to grant official status."""

    user_id: int
    official_title: Optional[str] = None


class OfficialRevoke(BaseModel):
    """Request to revoke official status."""

    user_id: int


class OfficialListItem(BaseModel):
    """Official user in list view."""

    id: int
    email: str
    username: str
    display_name: str
    official_title: Optional[str]
    official_verified_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class OfficialRequestItem(BaseModel):
    """User requesting official status (pending approval)."""

    id: int
    email: str
    username: str
    display_name: str
    official_title_request: Optional[str]
    official_request_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# Category Schemas
class CategoryBase(BaseModel):
    name_en: str
    name_fr: str
    description_en: Optional[str] = None
    description_fr: Optional[str] = None


class CategoryUpdate(BaseModel):
    name_en: Optional[str] = None
    name_fr: Optional[str] = None
    description_en: Optional[str] = None
    description_fr: Optional[str] = None


class CategoryCreate(CategoryBase):
    pass


class Category(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class CategoryStatistics(BaseModel):
    """Statistics for a single category."""

    category_id: int
    category_name_en: str
    category_name_fr: str
    total_ideas: int
    approved_ideas: int
    pending_ideas: int
    rejected_ideas: int


# ============================================================================
# Admin Statistics Schemas (REFACTOR-004)
# ============================================================================


class IdeaStatistics(BaseModel):
    """Statistics for a single idea (admin view)."""

    idea_id: int
    title: str
    status: str
    created_at: datetime
    validated_at: Optional[datetime]
    upvotes: int
    downvotes: int
    score: int
    comments: int


class UserIdeaStats(BaseModel):
    """Nested idea statistics for user stats."""

    total: int
    approved: int
    pending: int
    rejected: int


class UserVotesCast(BaseModel):
    """Nested votes cast statistics."""

    total: int
    upvotes: int
    downvotes: int


class UserVotesReceived(BaseModel):
    """Nested votes received statistics."""

    total: int
    upvotes: int
    downvotes: int
    score: int


class UserFlagsReceived(BaseModel):
    """Nested flags received statistics."""

    total: int
    on_ideas: int
    on_comments: int


class UserPenaltyStats(BaseModel):
    """Nested penalty statistics."""

    total: int
    active: int


class UserModerationStats(BaseModel):
    """Nested moderation statistics."""

    trust_score: int
    flags_received: UserFlagsReceived
    penalties: UserPenaltyStats


class UserStatistics(BaseModel):
    """Comprehensive user statistics (admin view)."""

    user_id: int
    username: str
    display_name: str
    email: str
    is_active: bool
    is_global_admin: bool
    created_at: datetime
    ideas: UserIdeaStats
    votes_cast: UserVotesCast
    votes_received: UserVotesReceived
    comments_made: int
    moderation: UserModerationStats


class AvatarUploadResponse(BaseModel):
    """Response after uploading an avatar."""

    message: str
    avatar_url: str


class SearchBackendInfo(BaseModel):
    """Information about the search backend."""

    backend: str
    available: bool


class SearchHealthStatus(BaseModel):
    """Health status of the search backend."""

    status: str
    backend: str
    message: str
    indexed_count: Optional[int] = None
    total_ideas: Optional[int] = None
    coverage_percent: Optional[float] = None


# Idea Schemas
class IdeaBase(BaseModel):
    title: str
    description: str
    category_id: int


class IdeaCreate(IdeaBase):
    tags: Optional[List[str]] = None  # List of tag names
    language: str = Field(
        default="fr",
        pattern="^(fr|en)$",
        description="Content language code (fr or en)",
    )


class IdeaUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None  # List of tag names


class IdeaModerate(BaseModel):
    status: IdeaStatus
    admin_comment: Optional[str] = None


class IdeaWithScore(BaseModel):
    id: int
    title: str
    description: str
    category_id: int
    user_id: int
    status: IdeaStatus
    admin_comment: Optional[str]
    created_at: datetime
    validated_at: Optional[datetime]
    author_username: str
    author_display_name: str
    category_name_en: str
    category_name_fr: str
    upvotes: int
    downvotes: int
    score: int
    user_vote: Optional[VoteType] = None
    comment_count: int
    tags: List["Tag"] = []  # List of tags
    quality_counts: Optional["QualityCounts"] = None  # Vote quality aggregations
    language: str = Field(default="fr", description="Content language code (fr/en)")

    model_config = ConfigDict(from_attributes=True)


class Idea(BaseModel):
    id: int
    title: str
    description: str
    category_id: int
    user_id: int
    status: IdeaStatus
    admin_comment: Optional[str]
    created_at: datetime
    validated_at: Optional[datetime]
    tags: List["Tag"] = []  # List of tags
    language: str = Field(default="fr", description="Content language code (fr/en)")

    model_config = ConfigDict(from_attributes=True)


# Vote Schemas
class VoteCreate(BaseModel):
    vote_type: VoteType
    quality_keys: Optional[List[str]] = None  # Optional quality keys for upvotes


class Vote(BaseModel):
    id: int
    idea_id: int
    user_id: int
    vote_type: VoteType
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VoteWithQualities(Vote):
    """Vote with associated quality keys."""

    qualities: List[
        str
    ] = []  # List of quality keys (e.g., ['community_benefit', 'urgent'])


# Comment Schemas
class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    language: str = Field(
        default="fr",
        pattern="^(fr|en)$",
        description="Comment language code (fr or en)",
    )


class CommentUpdate(BaseModel):
    is_moderated: bool


class Comment(CommentBase):
    id: int
    idea_id: int
    user_id: int
    is_moderated: bool
    created_at: datetime
    author_username: str
    author_display_name: str
    # Moderation status fields (for user's own comment view)
    is_deleted: Optional[bool] = None
    deletion_reason: Optional[str] = None
    is_hidden: Optional[bool] = None
    # Like fields
    like_count: int = 0
    user_has_liked: Optional[bool] = None  # None when not authenticated
    # Language tracking
    language: str = Field(default="fr", description="Comment language code (fr/en)")

    model_config = ConfigDict(from_attributes=True)


class CommentLikeResponse(BaseModel):
    """Response for comment like toggle."""

    liked: bool
    like_count: int

    model_config = ConfigDict(from_attributes=True)


# Admin Role Schemas
class AdminRoleCreate(BaseModel):
    user_id: int
    category_id: Optional[int] = None


class AdminRole(BaseModel):
    id: int
    user_id: int
    category_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)


# Content Validation Schemas
class ContentValidation(BaseModel):
    text: str
    language: str  # 'en' or 'fr'


class ValidationResult(BaseModel):
    is_valid: bool
    offensive_words: List[str] = []
    message: Optional[str] = None


# Tag Schemas
class TagBase(BaseModel):
    display_name: str


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    id: int
    name: str  # Normalized lowercase name
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TagWithCount(Tag):
    idea_count: int


class TagStatistics(BaseModel):
    tag: Tag
    total_ideas: int
    approved_ideas: int
    pending_ideas: int


# Similar Ideas Schemas
class SimilarIdeaRequest(BaseModel):
    title: str
    description: str
    category_id: Optional[int] = None


class SimilarIdea(BaseModel):
    id: int
    title: str
    description: str
    score: int
    similarity_score: float  # 0.0 to 1.0

    model_config = ConfigDict(from_attributes=True)


# Idea Merge Schema
class IdeaMerge(BaseModel):
    source_idea_id: int  # Idea to merge from
    target_idea_id: int  # Idea to merge into


# Idea Deletion Schemas
class IdeaDeleteRequest(BaseModel):
    """Request schema for deleting an idea (user)."""

    reason: Optional[str] = Field(
        None,
        max_length=500,
        description="Reason for deletion (optional for user)",
    )


class AdminIdeaDeleteRequest(BaseModel):
    """Request schema for admin deleting an idea (reason required)."""

    reason: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Reason for deletion (required for admin audit trail)",
    )


class IdeaDeleteResponse(BaseModel):
    """Response schema after deleting an idea."""

    message: str
    idea_id: int


class DeletedIdeaSummary(BaseModel):
    """Summary of a deleted idea for admin listing."""

    id: int
    title: str
    status: IdeaStatus
    deleted_at: datetime
    deleted_by_id: Optional[int]
    deleted_by_name: Optional[str]
    deletion_reason: Optional[str]
    original_author_id: int
    original_author_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeletedIdeasListResponse(BaseModel):
    """Paginated list of deleted ideas for admin."""

    items: List[DeletedIdeaSummary]
    total: int
    skip: int
    limit: int


class IdeaRestoreResponse(BaseModel):
    """Response schema after restoring an idea."""

    message: str
    idea_id: int


class RejectedIdeaSummary(BaseModel):
    """Summary of a rejected idea for admin listing."""

    id: int
    title: str
    admin_comment: Optional[str]
    author_id: int
    author_name: str
    category_id: int
    category_name_en: str
    category_name_fr: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RejectedIdeasListResponse(BaseModel):
    """Paginated list of rejected ideas for admin."""

    items: List[RejectedIdeaSummary]
    total: int
    skip: int
    limit: int


# Analytics Schemas


class Granularity(str, Enum):
    """Time granularity for trend data."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class OverviewMetrics(BaseModel):
    """Summary metrics for dashboard overview."""

    total_users: int
    active_users: int
    total_ideas: int
    approved_ideas: int
    pending_ideas: int
    rejected_ideas: int
    total_votes: int
    total_comments: int
    ideas_this_week: int
    votes_this_week: int
    comments_this_week: int
    users_this_week: int
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrendDataPoint(BaseModel):
    """Single data point in a trend series."""

    period: str  # ISO week "2025-W01", date "2025-01-15", or month "2025-01"
    ideas: int
    votes: int
    comments: int
    users: int


class TrendsResponse(BaseModel):
    """Time-series trend data."""

    granularity: Granularity
    start_date: datetime
    end_date: datetime
    data: List[TrendDataPoint]


class CategoryAnalytics(BaseModel):
    """Analytics for a single category."""

    id: int
    name_en: str
    name_fr: str
    total_ideas: int
    approved_ideas: int
    pending_ideas: int
    rejected_ideas: int
    total_votes: int
    total_comments: int
    avg_score: float
    approval_rate: float  # 0.0 to 1.0


class CategoriesAnalyticsResponse(BaseModel):
    """Analytics for all categories."""

    categories: List[CategoryAnalytics]
    generated_at: datetime


class ContributorType(str, Enum):
    """Type of contributor ranking."""

    IDEAS = "ideas"
    VOTES = "votes"
    COMMENTS = "comments"
    SCORE = "score"


class TopContributor(BaseModel):
    """Single contributor in rankings."""

    user_id: int
    display_name: str
    username: str
    count: int  # or score for score type
    rank: int


class TopContributorsResponse(BaseModel):
    """Top contributors response."""

    type: ContributorType
    contributors: List[TopContributor]
    generated_at: datetime


class CacheRefreshResponse(BaseModel):
    """Response for cache refresh endpoint."""

    message: str
    key: str


# ============================================================================
# Quality Analytics Schemas
# ============================================================================


class QualityDistribution(BaseModel):
    """Count for a single quality type."""

    quality_key: str
    quality_name_en: str
    quality_name_fr: str
    icon: Optional[str] = None
    color: Optional[str] = None
    count: int
    percentage: float


class TopIdeaByQuality(BaseModel):
    """An idea with high quality endorsements."""

    id: int
    title: str
    count: int


class QualityTopIdeas(BaseModel):
    """Top ideas for a specific quality."""

    quality_key: str
    quality_name_en: str
    quality_name_fr: str
    icon: Optional[str] = None
    color: Optional[str] = None
    ideas: List[TopIdeaByQuality]


class QualityAnalyticsResponse(BaseModel):
    """Response for quality analytics endpoint."""

    total_upvotes: int
    votes_with_qualities: int
    adoption_rate: float  # percentage of upvotes with qualities
    distribution: List[QualityDistribution]
    top_ideas_by_quality: List[QualityTopIdeas]
    generated_at: datetime


# ============================================================================
# Content Moderation Schemas
# ============================================================================


# --- Flag Schemas ---


class FlagCreate(BaseModel):
    """Schema for creating a content flag."""

    content_type: ContentType
    content_id: int
    reason: FlagReason
    details: Optional[str] = Field(None, max_length=500)


class FlagResponse(BaseModel):
    """Schema for flag response."""

    id: int
    content_type: ContentType
    content_id: int
    reporter_id: int
    reason: FlagReason
    details: Optional[str]
    status: FlagStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FlagWithReporter(FlagResponse):
    """Flag with reporter details (admin view)."""

    reporter_username: str
    reporter_display_name: str


class FlagReview(BaseModel):
    """Schema for reviewing flags."""

    flag_ids: List[int]
    action: str = Field(..., pattern="^(dismiss|action)$")
    review_notes: Optional[str] = Field(None, max_length=1000)
    issue_penalty: bool = False
    penalty_type: Optional[PenaltyType] = None
    penalty_reason: Optional[str] = None


# --- Penalty Schemas ---


class PenaltyCreate(BaseModel):
    """Schema for issuing a penalty."""

    user_id: int
    penalty_type: PenaltyType
    reason: str = Field(..., min_length=10, max_length=2000)
    related_flag_ids: Optional[List[int]] = None
    bulk_delete_content: bool = False


class PenaltyResponse(BaseModel):
    """Schema for penalty response."""

    id: int
    user_id: int
    penalty_type: PenaltyType
    reason: str
    status: PenaltyStatus
    issued_by: int
    issued_at: datetime
    expires_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class PenaltyWithUser(PenaltyResponse):
    """Penalty with user details (admin view)."""

    user_username: str
    user_display_name: str
    issuer_username: str
    can_appeal: bool


class PenaltyRevoke(BaseModel):
    """Schema for revoking a penalty."""

    reason: str = Field(..., min_length=10, max_length=1000)


# --- Appeal Schemas ---


class AppealCreate(BaseModel):
    """Schema for creating an appeal."""

    penalty_id: int
    reason: str = Field(..., min_length=50, max_length=2000)


class AppealResponse(BaseModel):
    """Schema for appeal response."""

    id: int
    penalty_id: int
    user_id: int
    reason: str
    status: AppealStatus
    created_at: datetime
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class AppealReview(BaseModel):
    """Schema for reviewing an appeal."""

    action: str = Field(..., pattern="^(approve|reject)$")
    review_notes: str = Field(..., min_length=10, max_length=1000)


# --- Keyword Watchlist Schemas ---


class KeywordCreate(BaseModel):
    """Schema for adding a keyword to watchlist."""

    keyword: str = Field(..., min_length=2, max_length=100)
    is_regex: bool = False
    auto_flag_reason: FlagReason = FlagReason.SPAM


class KeywordUpdate(BaseModel):
    """Schema for updating a keyword."""

    is_regex: Optional[bool] = None
    auto_flag_reason: Optional[FlagReason] = None
    is_active: Optional[bool] = None


class KeywordResponse(BaseModel):
    """Schema for keyword response."""

    id: int
    keyword: str
    is_regex: bool
    auto_flag_reason: FlagReason
    is_active: bool
    match_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Admin Note Schemas ---


class AdminNoteCreate(BaseModel):
    """Schema for creating an admin note."""

    content: str = Field(..., min_length=1, max_length=5000)


class AdminNoteUpdate(BaseModel):
    """Schema for updating an admin note."""

    content: str = Field(..., min_length=1, max_length=5000)


class AdminNoteResponse(BaseModel):
    """Schema for admin note response."""

    id: int
    user_id: int
    content: str
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime]
    author_username: str
    author_display_name: str

    model_config = ConfigDict(from_attributes=True)


# --- Moderation Queue Schemas ---


class FlaggedContentItem(BaseModel):
    """Schema for flagged content in moderation queue."""

    content_type: ContentType
    content_id: int
    content_text: str  # Preview of the content
    content_author_id: int
    content_author_username: str
    content_created_at: datetime
    flag_count: int
    is_hidden: bool
    flags: List[FlagWithReporter]
    author_trust_score: int
    author_total_flags: int
    idea_id: Optional[int] = None  # For comments: links to parent idea


class ModerationQueueResponse(BaseModel):
    """Schema for moderation queue response."""

    items: List[FlaggedContentItem]
    total: int
    pending_count: int


class FlaggedUserSummary(BaseModel):
    """Schema for flagged user in admin view."""

    user_id: int
    username: str
    display_name: str
    trust_score: int
    total_flags_received: int
    valid_flags_received: int
    pending_flags_count: int
    has_active_penalty: bool
    active_penalty_type: Optional[PenaltyType]


class FlaggedUsersResponse(BaseModel):
    """Schema for flagged users list."""

    users: List[FlaggedUserSummary]
    total: int


# --- Moderation Stats Schemas ---


class ModerationStats(BaseModel):
    """Schema for moderation statistics."""

    total_flags: int
    pending_flags: int
    resolved_today: int
    flags_by_reason: dict[str, int]
    flags_by_day: List[dict]  # [{date: str, count: int}]
    top_flagged_users: List[FlaggedUserSummary]
    active_penalties: int
    pending_appeals: int


# --- User Extensions for Moderation ---


class UserModerationInfo(BaseModel):
    """Extended user info for moderation."""

    trust_score: int
    approved_comments_count: int
    total_flags_received: int
    valid_flags_received: int
    flags_submitted_validated: int
    requires_comment_approval: bool
    has_active_penalty: bool
    penalty_history_count: int


# ============================================================================
# Paginated Response Schemas
# ============================================================================


class PaginatedIdeasResponse(BaseModel):
    """Paginated response for idea lists with total count."""

    items: List[IdeaWithScore]
    total: int
    skip: int
    limit: int
    has_more: bool

    model_config = ConfigDict(from_attributes=True)


class PendingIdeasResponse(PaginatedIdeasResponse):
    """Paginated response specifically for pending ideas in admin view."""

    pass


# ============================================================================
# Vote Qualities Schemas
# ============================================================================


class QualityBase(BaseModel):
    """Base schema for quality data."""

    key: str
    name_en: str
    name_fr: str
    description_en: Optional[str] = None
    description_fr: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_default: bool = True
    display_order: int = 0


class QualityCreate(QualityBase):
    """Schema for creating a new quality."""

    pass


class Quality(QualityBase):
    """Schema for a quality with all fields."""

    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QualityPublic(BaseModel):
    """Public-facing quality info (no admin fields)."""

    id: int
    key: str
    name_en: str
    name_fr: str
    description_en: Optional[str] = None
    description_fr: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    display_order: int

    model_config = ConfigDict(from_attributes=True)


class VoteQualityCreate(BaseModel):
    """Schema for attaching qualities to a vote."""

    quality_keys: List[
        str
    ]  # List of quality keys (e.g., ['community_benefit', 'urgent'])


class VoteQualitySchema(BaseModel):
    """Schema for a vote-quality association."""

    id: int
    vote_id: int
    quality_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QualityCount(BaseModel):
    """Count of votes for a specific quality on an idea."""

    quality_id: int
    quality_key: str
    count: int


class QualityCounts(BaseModel):
    """Aggregated quality counts for an idea."""

    counts: List[QualityCount] = []
    total_votes_with_qualities: int = 0


# ============================================================================
# Officials Analytics Schemas
# ============================================================================


class OfficialsQualityDistributionItem(BaseModel):
    """Quality distribution item for officials analytics."""

    quality_id: int
    key: str
    name_en: str
    name_fr: str
    icon: Optional[str]
    color: Optional[str]
    count: int


class OfficialsQualityOverview(BaseModel):
    """Quality overview response for officials."""

    total_upvotes: int
    votes_with_qualities: int
    adoption_rate: float
    quality_distribution: List[OfficialsQualityDistributionItem]


class OfficialsTopIdeaByQuality(BaseModel):
    """Top idea by quality for officials."""

    idea_id: int
    title: str
    category_name_en: str
    category_name_fr: str
    quality_count: int


class OfficialsCategoryQualityBreakdown(BaseModel):
    """Category quality breakdown for officials."""

    category_id: int
    name_en: str
    name_fr: str
    idea_count: int
    quality_count: int


class OfficialsTimeSeriesPoint(BaseModel):
    """Time series data point for officials."""

    date: str
    count: int


class OfficialsIdeaWithQualityStats(BaseModel):
    """Idea with quality statistics for officials."""

    id: int
    title: str
    description: str
    category_id: int
    status: str
    created_at: datetime
    quality_count: int
    score: int

    model_config = ConfigDict(from_attributes=True)


class OfficialsIdeasWithQualityResponse(BaseModel):
    """Paginated ideas with quality stats response for officials."""

    total: int
    items: List[OfficialsIdeaWithQualityStats]


class OfficialsIdeaQualityBreakdownItem(BaseModel):
    """Quality breakdown item for an idea."""

    quality_key: str
    quality_name_en: str
    quality_name_fr: str
    icon: Optional[str]
    color: Optional[str]
    count: int


class OfficialsTopComment(BaseModel):
    """Top comment for officials idea detail view."""

    id: int
    content: str
    author_display_name: str
    like_count: int
    created_at: datetime


class OfficialsIdeaDetail(BaseModel):
    """Detailed idea view for officials with quality breakdown."""

    id: int
    title: str
    description: str
    category_id: int
    category_name_en: str
    category_name_fr: str
    status: str
    created_at: datetime
    score: int
    upvotes: int
    downvotes: int
    quality_count: int
    quality_breakdown: List[OfficialsIdeaQualityBreakdownItem]
    author_display_name: str
    top_comments: List[OfficialsTopComment]


# ============================================================================
# Email Login Schemas
# ============================================================================


class EmailLoginRequest(BaseModel):
    """Request to initiate email login."""

    email: EmailStr

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "user@example.com"}}
    )


class EmailLoginResponse(BaseModel):
    """Response after requesting email login code."""

    message: str
    expires_in_seconds: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Login code sent to your email",
                "expires_in_seconds": 600,
            }
        }
    )


class EmailLoginVerify(BaseModel):
    """Request to verify email login code."""

    email: EmailStr
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit verification code",
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"email": "user@example.com", "code": "123456"}}
    )


class EmailLoginCodeInfo(BaseModel):
    """Internal schema for code management (admin use)."""

    id: int
    user_id: int
    created_at: datetime
    expires_at: datetime
    attempts: int
    used_at: Optional[datetime] = None
    ip_address: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EmailLoginStatusResponse(BaseModel):
    """Response for checking pending code status."""

    has_pending_code: bool
    expires_in_seconds: int = 0


# ============================================================================
# Two-Factor Authentication (2FA) Schemas
# ============================================================================


class TwoFactorSetupResponse(BaseModel):
    """Response for 2FA setup initiation."""

    secret: str = Field(..., description="Base32-encoded TOTP secret (show once)")
    provisioning_uri: str = Field(..., description="otpauth:// URI for QR code")
    qr_code_data: str = Field(..., description="Same as provisioning_uri for QR libs")


class TwoFactorVerifySetupRequest(BaseModel):
    """Request to verify 2FA setup with first TOTP code."""

    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit TOTP code from authenticator app",
    )


class TwoFactorVerifySetupResponse(BaseModel):
    """Response after successful 2FA setup."""

    enabled: bool
    backup_codes: List[str] = Field(
        ..., description="One-time backup codes (show once, cannot be retrieved)"
    )


class TwoFactorDisableRequest(BaseModel):
    """Request to disable 2FA (requires re-authentication)."""

    password: Optional[str] = Field(None, description="Current password")
    email_code: Optional[str] = Field(None, description="Email verification code")


class TwoFactorStatusResponse(BaseModel):
    """2FA status for current user."""

    enabled: bool
    backup_codes_remaining: int = 0


class TwoFactorLoginRequest(BaseModel):
    """Request to complete login with 2FA code."""

    temp_token: str = Field(..., description="Temporary token from initial login")
    code: str = Field(
        ...,
        min_length=6,
        max_length=8,
        description="6-digit TOTP code or 8-character backup code",
    )
    is_backup_code: bool = Field(
        default=False, description="True if using a backup code"
    )


class TwoFactorRequiredResponse(BaseModel):
    """Response when 2FA is required to complete login."""

    requires_2fa: bool = True
    temp_token: str = Field(..., description="Temp token for 2FA verification step")
    message: str = "Two-factor authentication required"


class BackupCodesResponse(BaseModel):
    """Response with newly generated backup codes."""

    backup_codes: List[str] = Field(
        ..., description="New backup codes (show once, invalidates previous codes)"
    )


class BackupCodesCountResponse(BaseModel):
    """Response with count of remaining backup codes."""

    remaining: int


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# ============================================================================
# Privacy Settings Schemas (Law 25 Compliance - Phase 4)
# ============================================================================


class ProfileVisibility(str, Enum):
    """Profile visibility options."""

    PUBLIC = "public"  # Anyone can see profile
    REGISTERED = "registered"  # Only logged-in users
    PRIVATE = "private"  # Profile hidden (only username shown)


class PrivacySettings(BaseModel):
    """User privacy settings."""

    profile_visibility: ProfileVisibility = Field(
        default=ProfileVisibility.PUBLIC, description="Who can see your profile"
    )
    show_display_name: bool = Field(
        default=True, description="Show your display name publicly"
    )
    show_avatar: bool = Field(default=True, description="Show your avatar publicly")
    show_activity: bool = Field(
        default=True, description="Show your ideas and comments on your profile"
    )
    show_join_date: bool = Field(
        default=True, description="Show when you joined the platform"
    )

    model_config = ConfigDict(from_attributes=True)


class PrivacySettingsUpdate(BaseModel):
    """Update user privacy settings."""

    profile_visibility: Optional[ProfileVisibility] = None
    show_display_name: Optional[bool] = None
    show_avatar: Optional[bool] = None
    show_activity: Optional[bool] = None
    show_join_date: Optional[bool] = None


class UserPublicFiltered(BaseModel):
    """
    Public user profile with privacy settings applied.

    Fields are Optional because they may be hidden based on settings.
    """

    id: int
    username: str
    display_name: Optional[str] = None  # Hidden if show_display_name=False
    avatar_url: Optional[str] = None  # Hidden if show_avatar=False
    is_official: bool = False
    official_title: Optional[str] = None
    created_at: Optional[datetime] = None  # Hidden if show_join_date=False
    idea_count: Optional[int] = None  # Hidden if show_activity=False
    comment_count: Optional[int] = None  # Hidden if show_activity=False
    profile_visibility: str = "public"

    model_config = ConfigDict(from_attributes=True)


class PolicyVersionInfo(BaseModel):
    """Information about a policy version."""

    version: str
    effective_date: datetime
    summary_en: Optional[str] = None
    summary_fr: Optional[str] = None
    requires_reconsent: bool = False

    model_config = ConfigDict(from_attributes=True)


class PolicyChangelogResponse(BaseModel):
    """Response for policy version changelog."""

    policy_type: str
    versions: List[PolicyVersionInfo]


class ReconsentCheck(BaseModel):
    """Check if user needs to re-consent."""

    requires_privacy_reconsent: bool = False
    requires_terms_reconsent: bool = False
    current_privacy_version: str
    current_terms_version: str
    user_privacy_version: Optional[str] = None
    user_terms_version: Optional[str] = None


class ReconsentRequest(BaseModel):
    """Request to re-consent to updated policies."""

    policy_type: str = Field(
        ...,
        pattern="^(privacy|terms)$",
        description="Policy type: 'privacy' or 'terms'",
    )


# ============================================================================
# Consent Management Schemas (Law 25 Compliance)
# ============================================================================


class ConsentUpdate(BaseModel):
    """Schema for updating consent preferences."""

    marketing_consent: Optional[bool] = Field(
        None, description="Update marketing consent preference"
    )
    # For re-consent after policy updates
    accepts_terms: Optional[bool] = Field(
        None, description="Re-accept Terms of Service (after update)"
    )
    accepts_privacy_policy: Optional[bool] = Field(
        None, description="Re-accept Privacy Policy (after update)"
    )


class ConsentStatus(BaseModel):
    """Schema for viewing current consent status."""

    terms_accepted: bool
    terms_version: Optional[str]
    privacy_accepted: bool
    privacy_version: Optional[str]
    marketing_consent: bool
    consent_timestamp: Optional[datetime]
    requires_reconsent: bool = Field(
        description="True if policies have been updated since user's last consent"
    )

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Privacy Incident Schemas (Law 25 Compliance - Phase 5)
# ============================================================================


class IncidentCreate(BaseModel):
    """Schema for creating a new privacy incident."""

    incident_type: str = Field(
        ...,
        description="Type: unauthorized_access, data_loss, data_breach, system_compromise",
    )
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    title: str = Field(..., max_length=200, description="Brief incident title")
    description: str = Field(..., description="Detailed description of the incident")
    occurred_at: Optional[datetime] = Field(
        None, description="When incident occurred (if known)"
    )
    affected_user_ids: Optional[List[int]] = Field(
        None, description="List of affected user IDs"
    )
    data_types: Optional[List[str]] = Field(
        None, description="List of data types involved (email, password, etc.)"
    )


class IncidentStatusUpdate(BaseModel):
    """Schema for updating incident status."""

    status: str = Field(
        ...,
        description="Status: open, investigating, contained, mitigated, closed",
    )
    notes: Optional[str] = Field(None, description="Notes about the status change")


class IncidentSummary(BaseModel):
    """Schema for incident list response."""

    id: int
    incident_number: str
    incident_type: str
    severity: str
    status: str
    title: str
    affected_users_count: int
    cai_notified: bool
    users_notified: bool
    discovered_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentDetail(BaseModel):
    """Schema for full incident details."""

    id: int
    incident_number: str
    incident_type: str
    severity: str
    status: str
    title: str
    description: str
    root_cause: Optional[str]
    discovered_at: datetime
    occurred_at: Optional[datetime]
    contained_at: Optional[datetime]
    resolved_at: Optional[datetime]
    affected_users_count: int
    data_types_involved: Optional[List[str]]
    risk_of_harm: str
    cai_notification_required: bool
    cai_notified: bool
    cai_notified_at: Optional[datetime]
    cai_reference_number: Optional[str]
    users_notification_required: bool
    users_notified: bool
    users_notified_at: Optional[datetime]
    mitigation_measures: Optional[str]
    preventive_measures: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class SecurityAuditLogResponse(BaseModel):
    """Schema for security audit log response."""

    id: int
    event_type: str
    severity: str
    user_id: Optional[int]
    action: str
    ip_address: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[int]
    success: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SecurityAlertsResponse(BaseModel):
    """Schema for security alerts response."""

    alerts: List[dict]
    count: int


class IncidentListResponse(BaseModel):
    """Schema for paginated incident list."""

    items: List[IncidentSummary]
    total: int
    skip: int
    limit: int


class IncidentCreateResponse(BaseModel):
    """Schema for incident creation response."""

    incident_number: str
    id: int


class IncidentStatusUpdateResponse(BaseModel):
    """Schema for incident status update response."""

    incident_number: str
    status: str


class CAINotificationResponse(BaseModel):
    """Schema for CAI notification response."""

    incident_number: str
    cai_notified: bool
    cai_notified_at: Optional[datetime]


class UserNotificationResponse(BaseModel):
    """Schema for user notification response."""

    incident_number: str
    users_notified: bool
    users_notified_at: Optional[datetime]


# ============================================================================
# Data Export Schemas (Law 25 Compliance - Phase 2)
# ============================================================================


class UserProfileExport(BaseModel):
    """User profile data for export."""

    id: int
    email: str
    username: str
    display_name: str
    avatar_url: Optional[str]
    created_at: datetime
    is_official: bool
    official_title: Optional[str]
    trust_score: int
    is_active: bool
    # Consent status
    consent_terms_accepted: bool
    consent_terms_version: Optional[str]
    consent_privacy_accepted: bool
    consent_privacy_version: Optional[str]
    consent_timestamp: Optional[datetime]
    marketing_consent: bool

    model_config = ConfigDict(from_attributes=True)


class IdeaExport(BaseModel):
    """Idea data for export."""

    id: int
    title: str
    description: str
    status: str
    category_id: int
    category_name: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    upvote_count: int
    downvote_count: int
    score: int
    tags: List[str]

    model_config = ConfigDict(from_attributes=True)


class CommentExport(BaseModel):
    """Comment data for export."""

    id: int
    content: str
    idea_id: int
    idea_title: Optional[str]
    created_at: datetime
    is_moderated: bool

    model_config = ConfigDict(from_attributes=True)


class VoteExport(BaseModel):
    """Vote data for export."""

    id: int
    idea_id: int
    idea_title: Optional[str]
    vote_type: str
    qualities: List[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsentLogExport(BaseModel):
    """Consent log entry for export."""

    consent_type: str
    action: str
    policy_version: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDataExport(BaseModel):
    """Complete user data export for Law 25 compliance."""

    export_date: datetime
    export_format: str = Field(description="json or csv")
    user_profile: UserProfileExport
    ideas: List[IdeaExport]
    comments: List[CommentExport]
    votes: List[VoteExport]
    consent_history: List[ConsentLogExport]

    model_config = ConfigDict(from_attributes=True)


class DeleteAccountRequest(BaseModel):
    """Request to delete user account."""

    password: str = Field(description="Current password for verification")
    confirmation_text: str = Field(
        description="User must type 'DELETE MY ACCOUNT' to confirm"
    )
    delete_content: bool = Field(
        default=False,
        description="If true, delete content. If false, anonymize content (keep for community).",
    )


class DeleteAccountResponse(BaseModel):
    """Response after account deletion."""

    message: str
    deleted_at: datetime
    data_deleted: bool
    content_anonymized: bool
