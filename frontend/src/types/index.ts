export interface User {
  id: number;
  email: string;
  username: string;
  display_name: string;
  avatar_url?: string;
  is_global_admin: boolean;
  is_active: boolean;
  is_official: boolean;
  official_title: string | null;
  created_at: string;
}

// Official Types
export interface OfficialInfo {
  is_official: boolean;
  official_title: string | null;
  official_verified_at: string | null;
}

// Officials Dashboard Analytics Types
export interface OfficialsQualityDistributionItem {
  quality_id: number;
  key: string;
  name_en: string;
  name_fr: string;
  icon: string | null;
  color: string | null;
  count: number;
}

export interface OfficialsQualityOverview {
  total_upvotes: number;
  votes_with_qualities: number;
  adoption_rate: number;
  quality_distribution: OfficialsQualityDistributionItem[];
}

export interface OfficialsTopIdeaByQuality {
  idea_id: number;
  title: string;
  category_name_en: string;
  category_name_fr: string;
  quality_count: number;
}

export interface OfficialsCategoryQualityBreakdown {
  category_id: number;
  name_en: string;
  name_fr: string;
  idea_count: number;
  quality_count: number;
}

export interface OfficialsTimeSeriesPoint {
  date: string;
  count: number;
}

export interface OfficialsIdeaWithQualityStats {
  id: number;
  title: string;
  description: string;
  category_id: number;
  score: number;
  quality_count: number;
  status: string;
  created_at: string;
}

export interface OfficialsIdeasWithQualityResponse {
  total: number;
  items: OfficialsIdeaWithQualityStats[];
}

export interface OfficialsIdeaQualityBreakdownItem {
  quality_key: string;
  quality_name_en: string;
  quality_name_fr: string;
  icon: string | null;
  color: string | null;
  count: number;
}

export interface OfficialsTopComment {
  id: number;
  content: string;
  author_display_name: string;
  like_count: number;
  created_at: string;
}

export interface OfficialsIdeaDetail {
  id: number;
  title: string;
  description: string;
  category_id: number;
  category_name_en: string;
  category_name_fr: string;
  status: string;
  created_at: string;
  score: number;
  upvotes: number;
  downvotes: number;
  quality_count: number;
  quality_breakdown: OfficialsIdeaQualityBreakdownItem[];
  author_display_name: string;
  top_comments: OfficialsTopComment[];
}

// Admin Official Management Types
export interface OfficialListItem {
  id: number;
  email: string;
  username: string;
  display_name: string;
  official_title: string | null;
  official_verified_at: string | null;
}

export interface PendingOfficialRequest {
  id: number;
  email: string;
  username: string;
  display_name: string;
  official_title_request: string | null;
  official_request_at: string;
}

export interface Category {
  id: number;
  name_en: string;
  name_fr: string;
  description_en?: string;
  description_fr?: string;
}

export interface CategoryCreate {
  name_en: string;
  name_fr: string;
  description_en?: string;
  description_fr?: string;
}

export interface CategoryStatistics {
  category_id: number;
  category_name_en: string;
  category_name_fr: string;
  total_ideas: number;
  approved_ideas: number;
  pending_ideas: number;
  rejected_ideas: number;
}

export type IdeaStatus = 'pending' | 'approved' | 'rejected';
export type VoteType = 'upvote' | 'downvote';
export type QualityType = 'community_benefit' | 'quality_of_life' | 'urgent' | 'would_volunteer';

export interface QualityCounts {
  community_benefit: number;
  quality_of_life: number;
  urgent: number;
  would_volunteer: number;
}

export interface VoteWithQualities {
  id: number;
  idea_id: number;
  user_id: number;
  vote_type: VoteType;
  created_at: string;
  qualities: QualityType[];
}

export interface Tag {
  id: number;
  name: string;
  display_name: string;
  created_at: string;
}

export interface TagWithCount extends Tag {
  idea_count: number;
}

export interface TagStatistics {
  tag: Tag;
  total_ideas: number;
  approved_ideas: number;
  pending_ideas: number;
}

export interface Idea {
  id: number;
  title: string;
  description: string;
  category_id: number;
  user_id: number;
  status: IdeaStatus;
  admin_comment?: string;
  created_at: string;
  validated_at?: string;
  author_username: string;
  author_display_name: string;
  category_name_en: string;
  category_name_fr: string;
  upvotes: number;
  downvotes: number;
  score: number;
  user_vote?: VoteType;
  comment_count: number;
  tags: Tag[];
  quality_counts?: QualityCounts;
  language?: 'fr' | 'en';
}

export interface Comment {
  id: number;
  idea_id: number;
  user_id: number;
  content: string;
  is_moderated: boolean;
  created_at: string;
  author_username: string;
  author_display_name: string;
  // Moderation status (for user's own comment view)
  is_deleted?: boolean;
  deletion_reason?: string;
  is_hidden?: boolean;
  // Like fields
  like_count: number;
  user_has_liked: boolean | null; // null when not authenticated
  language?: 'fr' | 'en';
}

export interface CommentLikeResponse {
  liked: boolean;
  like_count: number;
}

export interface IdeaCreate {
  title: string;
  description: string;
  category_id: number;
  tags?: string[];
  language?: 'fr' | 'en';
}

export interface IdeaUpdate {
  title?: string;
  description?: string;
  category_id?: number;
  tags?: string[];
}

export interface SimilarIdeaRequest {
  title: string;
  description: string;
  category_id?: number;
}

export interface SimilarIdea {
  id: number;
  title: string;
  description: string;
  score: number;
  similarity_score: number;
}

export interface CommentCreate {
  content: string;
  language?: 'fr' | 'en';
}

export interface VoteCreate {
  vote_type: VoteType;
  quality_keys?: QualityType[];
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  display_name: string;
  requests_official_status?: boolean;
  official_title_request?: string | null;
  // Law 25 consent fields
  accepts_terms: boolean;
  accepts_privacy_policy: boolean;
  marketing_consent?: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// Email Login Types
export interface EmailLoginRequest {
  email: string;
}

export interface EmailLoginResponse {
  message: string;
  expires_in_seconds: number;
}

export interface EmailLoginVerify {
  email: string;
  code: string;
}

export interface EmailLoginStatus {
  has_pending_code: boolean;
  expires_in_seconds: number;
}

export interface UserManagement {
  id: number;
  email: string;
  username: string;
  display_name: string;
  is_active: boolean;
  is_global_admin: boolean;
  is_official: boolean;
  official_title: string | null;
  has_category_admin_role: boolean;
  created_at: string;
  // Reputation fields for badges
  trust_score: number; // 0-100
  vote_score: number; // upvotes - downvotes received
  penalty_count: number; // total penalties
  active_penalty_count: number; // currently active penalties
}

// User filter types for admin users endpoint
export type UserRole = 'regular' | 'category_admin' | 'global_admin' | 'official';

export interface UserFilterParams {
  page?: number;
  page_size?: number;
  search?: string;
  include_inactive?: boolean;
  role?: UserRole;
  is_official?: boolean;
  is_banned?: boolean;
  trust_score_min?: number;
  trust_score_max?: number;
  vote_score_min?: number;
  vote_score_max?: number;
  has_penalties?: boolean;
  has_active_penalties?: boolean;
  created_after?: string;
  created_before?: string;
}

export interface UserListResponse {
  users: UserManagement[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface UserUpdate {
  is_active?: boolean;
  is_global_admin?: boolean;
}

export interface UserStatistics {
  user_id: number;
  username: string;
  display_name: string;
  email: string;
  is_active: boolean;
  is_global_admin: boolean;
  created_at: string;
  ideas: {
    total: number;
    approved: number;
    pending: number;
    rejected: number;
  };
  votes_cast: {
    total: number;
    upvotes: number;
    downvotes: number;
  };
  votes_received: {
    total: number;
    upvotes: number;
    downvotes: number;
    score: number;
  };
  comments_made: number;
  moderation: {
    trust_score: number;
    flags_received: {
      total: number;
      on_ideas: number;
      on_comments: number;
    };
    penalties: {
      total: number;
      active: number;
    };
  };
}

export interface UserProfileUpdate {
  display_name?: string;
  email?: string;
}

export interface PasswordChange {
  current_password: string;
  new_password: string;
}

export interface UserActivityHistory {
  ideas_count: number;
  approved_ideas_count: number;
  pending_ideas_count: number;
  rejected_ideas_count: number;
  votes_count: number;
  comments_count: number;
  recent_ideas: Idea[];
  recent_comments: Comment[];
}

// Search types
export interface SearchFilters {
  category_id?: number;
  category_ids?: number[];
  status?: string;
  author_id?: number;
  from_date?: string;
  to_date?: string;
  language?: string;
  tag_names?: string[];
  min_score?: number;
  has_comments?: boolean;
}

export interface SearchHighlight {
  title?: string;
  description?: string;
}

export interface SearchResultItem {
  idea: Idea;
  relevance_score: number;
  highlights?: SearchHighlight;
}

export interface SearchResults {
  query: string;
  total: number;
  results: SearchResultItem[];
  filters_applied: SearchFilters;
  search_backend: string;
}

export interface TagSuggestion {
  name: string;
  display_name: string;
  idea_count: number;
}

export interface AutocompleteResult {
  ideas: string[];
  tags: TagSuggestion[];
  queries?: string[];
}

export interface SearchQueryParams {
  q: string;
  skip?: number;
  limit?: number;
  highlight?: boolean;
  filters?: SearchFilters;
}

// Deleted idea summary for admin listing
export interface DeletedIdeaSummary {
  id: number;
  title: string;
  status: IdeaStatus;
  deleted_at: string;
  deleted_by_id: number | null;
  deleted_by_name: string | null;
  deletion_reason: string | null;
  original_author_id: number;
  original_author_name: string;
  created_at: string;
}

// Response types for delete/restore operations
export interface IdeaDeleteResponse {
  message: string;
  idea_id: number;
}

export interface IdeaRestoreResponse {
  message: string;
  idea_id: number;
}

export interface DeletedIdeasListResponse {
  items: DeletedIdeaSummary[];
  total: number;
  skip: number;
  limit: number;
}

// Rejected idea summary for admin listing
export interface RejectedIdeaSummary {
  id: number;
  title: string;
  admin_comment: string | null;
  author_id: number;
  author_name: string;
  category_id: number;
  category_name_en: string;
  category_name_fr: string;
  created_at: string;
}

export interface RejectedIdeasListResponse {
  items: RejectedIdeaSummary[];
  total: number;
  skip: number;
  limit: number;
}

// Analytics Types
export type Granularity = 'day' | 'week' | 'month';
export type ContributorType = 'ideas' | 'votes' | 'comments' | 'score';

export interface OverviewMetrics {
  total_users: number;
  active_users: number;
  total_ideas: number;
  approved_ideas: number;
  pending_ideas: number;
  rejected_ideas: number;
  total_votes: number;
  total_comments: number;
  ideas_this_week: number;
  votes_this_week: number;
  comments_this_week: number;
  users_this_week: number;
  generated_at: string;
}

export interface TrendDataPoint {
  period: string;
  ideas: number;
  votes: number;
  comments: number;
  users: number;
}

export interface TrendsResponse {
  granularity: Granularity;
  start_date: string;
  end_date: string;
  data: TrendDataPoint[];
}

export interface CategoryAnalytics {
  id: number;
  name_en: string;
  name_fr: string;
  total_ideas: number;
  approved_ideas: number;
  pending_ideas: number;
  rejected_ideas: number;
  total_votes: number;
  total_comments: number;
  avg_score: number;
  approval_rate: number;
}

export interface CategoriesAnalyticsResponse {
  categories: CategoryAnalytics[];
  generated_at: string;
}

export interface TopContributor {
  user_id: number;
  display_name: string;
  username: string;
  count: number;
  rank: number;
}

export interface TopContributorsResponse {
  type: ContributorType;
  contributors: TopContributor[];
  generated_at: string;
}

// Quality Analytics Types
export interface QualityDistribution {
  quality_key: string;
  quality_name_en: string;
  quality_name_fr: string;
  icon: string | null;
  color: string | null;
  count: number;
  percentage: number;
}

export interface TopIdeaByQuality {
  id: number;
  title: string;
  count: number;
}

export interface QualityTopIdeas {
  quality_key: string;
  quality_name_en: string;
  quality_name_fr: string;
  icon: string | null;
  color: string | null;
  ideas: TopIdeaByQuality[];
}

export interface QualityAnalyticsResponse {
  total_upvotes: number;
  votes_with_qualities: number;
  adoption_rate: number;
  distribution: QualityDistribution[];
  top_ideas_by_quality: QualityTopIdeas[];
  generated_at: string;
}

export interface DateRange {
  startDate: Date;
  endDate: Date;
}

export type DateRangePreset =
  | 'last7days'
  | 'last30days'
  | 'last90days'
  | 'thisYear'
  | 'lastYear'
  | 'allTime'
  | 'custom';

// Paginated response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export type PendingIdeasResponse = PaginatedResponse<Idea>;

// Admin Notification Types (ntfy viewer)
export interface AdminNotification {
  id: string;
  timestamp: string; // ISO 8601
  topic: string;
  topic_display: string;
  title: string;
  message: string;
  priority: 'min' | 'low' | 'default' | 'high' | 'max';
  priority_level: number; // 1-5
  tags: string[];
  click_url: string | null;
}

export interface AdminNotificationCounts {
  ideas?: number;
  comments?: number;
  appeals?: number;
  officials?: number;
  reports?: number;
  critical?: number;
}

// ============================================================================
// Consent Types (Law 25 Compliance)
// ============================================================================

export interface ConsentStatus {
  terms_accepted: boolean;
  terms_version: string | null;
  privacy_accepted: boolean;
  privacy_version: string | null;
  marketing_consent: boolean;
  consent_timestamp: string | null;
  requires_reconsent: boolean;
}

export interface ConsentLogEntry {
  consent_type: string;
  action: string;
  policy_version: string | null;
  created_at: string;
}

// Diagnostics Types
export interface TableInfo {
  name: string;
  row_count: number | null;
}

export interface PoolInfo {
  pool_size: number | null;
  checked_in: number;
  checked_out: number;
  overflow: number;
  invalid: number | null;
}

export interface DatabaseDiagnosticsResponse {
  connected: boolean;
  database_type: string;
  database_url_masked: string;
  tables: TableInfo[];
  pool_info: PoolInfo | null;
  error: string | null;
}
