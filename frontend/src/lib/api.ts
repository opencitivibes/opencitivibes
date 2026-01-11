import axios from 'axios';
import { setTag, getActiveSpan, withScope, captureException, startSpan } from '@/lib/sentry-utils';
import { toast } from 'sonner';
import i18n from '@/i18n/config';
import type {
  User,
  Category,
  CategoryCreate,
  CategoryStatistics,
  Idea,
  Comment,
  CommentLikeResponse,
  IdeaCreate,
  CommentCreate,
  VoteCreate,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  UserManagement,
  UserUpdate,
  UserStatistics,
  UserListResponse,
  UserFilterParams,
  UserProfileUpdate,
  PasswordChange,
  UserActivityHistory,
  SimilarIdeaRequest,
  SimilarIdea,
  SearchQueryParams,
  SearchResults,
  AutocompleteResult,
  IdeaDeleteResponse,
  DeletedIdeasListResponse,
  IdeaRestoreResponse,
  RejectedIdeasListResponse,
  OverviewMetrics,
  TrendsResponse,
  CategoriesAnalyticsResponse,
  TopContributorsResponse,
  Granularity,
  ContributorType,
  PendingIdeasResponse,
  QualityType,
  VoteWithQualities,
  QualityAnalyticsResponse,
  OfficialsQualityOverview,
  OfficialsTopIdeaByQuality,
  OfficialsCategoryQualityBreakdown,
  OfficialsTimeSeriesPoint,
  OfficialsIdeasWithQualityResponse,
  OfficialsIdeaDetail,
  OfficialListItem,
  PendingOfficialRequest,
  EmailLoginResponse,
  EmailLoginStatus,
  AdminNotification,
  AdminNotificationCounts,
  ConsentStatus,
  ConsentLogEntry,
  DatabaseDiagnosticsResponse,
  SystemResourcesResponse,
  SharePlatform,
  ShareAnalyticsResponse,
  SecurityEventsResponse,
  SecuritySummary,
  TwoFactorSetupResponse,
  TwoFactorVerifySetupResponse,
  TwoFactorStatusResponse,
  TwoFactorDisableRequest,
  LoginResponse,
  AdminRole,
  AdminRoleCreate,
  QualitySignalsResponse,
  WeightedScoreResponse,
  ScoreAnomaliesResponse,
  TrustedDevice,
  TrustedDeviceListResponse,
  TokenWithDeviceToken,
  TwoFactorLoginWithTrustRequest,
  PasswordResetRequestResponse,
  PasswordResetVerifyResponse,
  PasswordResetCompleteResponse,
} from '@/types';
import { getDeviceToken, setDeviceToken, clearDeviceToken } from '@/lib/deviceToken';
import type {
  FlagCreate,
  FlagResponse,
  FlagCheckResponse,
  AppealCreate,
  AppealResponse,
  ContentType,
  FlagReason,
  PenaltyType,
  ModerationQueueResponse,
  FlagWithReporter,
  FlaggedUserSummary,
  ModerationStats,
  AdminNote,
  KeywordEntry,
  PendingComment,
  PenaltyResponse,
} from '@/types/moderation';

// Determine API URL at runtime for mobile testing support
export function getApiUrl(): string {
  // Server-side: use env variable or default
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
  }

  // Client-side: check for baked-in env var first
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  // Fallback for local development: use same host as frontend
  const { protocol, hostname } = window.location;

  // If accessing via localhost or local IP (192.168.x.x), use port 8000 for backend
  if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.')) {
    return `${protocol}//${hostname}:8000/api`;
  }

  // Production: use relative /api path (nginx proxies to backend)
  return '/api';
}

// Get base URL (without /api) for static files like avatars
export function getApiBaseUrl(): string {
  return getApiUrl().replace('/api', '');
}

const API_URL = getApiUrl();

const api = axios.create({
  baseURL: API_URL,
});

// Callback for handling authentication failures
let onAuthFailure: (() => void) | null = null;

export const setAuthFailureHandler = (handler: () => void) => {
  onAuthFailure = handler;
};

// Generate a short random ID (fallback for non-secure contexts like HTTP on mobile)
function generateCorrelationId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID().slice(0, 8);
  }
  // Fallback for HTTP contexts where crypto.randomUUID is unavailable
  return Math.random().toString(36).substring(2, 10);
}

// Add auth token, correlation ID, Accept-Language, and Sentry trace headers to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Generate correlation ID for this request
  const correlationId = generateCorrelationId();

  // Add to headers
  config.headers['X-Correlation-ID'] = correlationId;

  // Add Accept-Language header based on current UI language
  // This enables language-aware content prioritization on the backend
  const uiLanguage = i18n.language?.substring(0, 2) || 'fr';
  config.headers['Accept-Language'] = uiLanguage;

  // Set in Sentry for this request (no-op if Sentry disabled)
  setTag('correlation_id', correlationId);

  // Add Sentry trace headers for distributed tracing
  const activeSpan = getActiveSpan();
  if (activeSpan) {
    const spanContext = activeSpan.spanContext();
    const traceId = spanContext.traceId;
    const spanId = spanContext.spanId;
    // sentry-trace format: {traceId}-{spanId}-{sampled}
    const sampled = (spanContext.traceFlags & 0x01) === 0x01 ? '1' : '0';
    config.headers['sentry-trace'] = `${traceId}-${spanId}-${sampled}`;
    config.headers['baggage'] =
      `sentry-trace_id=${traceId},sentry-environment=${process.env.NEXT_PUBLIC_ENVIRONMENT || 'development'}`;
  }

  return config;
});

// Define error response types
interface ValidationError {
  type: string;
  loc: string[];
  msg: string;
  input?: unknown;
}

interface ApiErrorResponse {
  detail: string | ValidationError[];
  type?: string;
  correlation_id?: string;
}

// Handle errors globally with Sentry integration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Extract correlation ID from response
    const correlationId: string | undefined =
      error.response?.data?.correlation_id || error.response?.headers?.['x-correlation-id'];

    // Set Sentry context (no-op if Sentry disabled)
    if (correlationId) {
      setTag('correlation_id', correlationId);
    }

    // Capture in Sentry with context (no-op if Sentry disabled)
    withScope((scope) => {
      scope.setTag('correlation_id', correlationId || 'unknown');
      scope.setExtra('url', error.config?.url);
      scope.setExtra('method', error.config?.method);
      scope.setExtra('status', error.response?.status);

      // Only capture unexpected errors (not 4xx which are expected)
      if (!error.response || error.response.status >= 500) {
        captureException(error);
      }
    });

    // Network error (no response from server)
    if (!error.response) {
      const message = i18n.t('toast.networkError');
      toast.error(message, {
        description: correlationId ? `Reference: ${correlationId}` : undefined,
        duration: 6000,
      });
      return Promise.reject(error);
    }

    const { status } = error.response;
    const requestUrl = error.config?.url || '';
    const errorData = error.response.data as ApiErrorResponse | undefined;

    // Handle 401 Unauthorized
    if (status === 401) {
      // Don't trigger global logout for auth endpoints (login/register)
      // These should handle their own errors
      const isAuthEndpoint =
        requestUrl.includes('/auth/login') || requestUrl.includes('/auth/register');

      if (!isAuthEndpoint) {
        // Clear token from localStorage
        if (typeof window !== 'undefined') {
          localStorage.removeItem('token');
        }

        // Show session expired toast
        toast.error(i18n.t('toast.sessionExpired'), {
          duration: 5000,
        });

        // Call the auth failure handler (logout and redirect)
        if (onAuthFailure) {
          onAuthFailure();
        }

        // For non-auth endpoints, resolve with an empty response to prevent
        // React component crashes when session expires during data fetching.
        // The onAuthFailure handler takes care of redirect/cleanup.
        return Promise.resolve({ data: null, status: 401 });
      }
    }

    // Handle 500+ server errors with correlation ID
    if (status >= 500) {
      const message = i18n.t('toast.error');
      toast.error(message, {
        description: correlationId ? `Reference: ${correlationId}` : undefined,
        duration: 6000,
      });
    }

    // Handle 4xx errors with correlation ID (validation, not found, etc.)
    if (status >= 400 && status < 500 && status !== 401) {
      const detail = errorData?.detail;
      let message: string;

      // Handle FastAPI validation errors (array of objects with msg field)
      if (Array.isArray(detail)) {
        message = detail.map((e) => e.msg).join(', ');
      } else if (typeof detail === 'string') {
        message = detail;
      } else {
        message = i18n.t('toast.error');
      }

      toast.error(message, {
        description: correlationId ? `Reference: ${correlationId}` : undefined,
        duration: 5000,
      });
    }

    return Promise.reject(error);
  }
);

// Auth APIs
export const authAPI = {
  register: async (data: RegisterRequest): Promise<User> => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },

  login: async (data: LoginRequest): Promise<LoginResponse> => {
    const formData = new FormData();
    formData.append('username', data.username);
    formData.append('password', data.password);

    // Include device token if available (for trusted device 2FA bypass)
    const deviceToken = getDeviceToken();
    const headers: Record<string, string> = {};
    if (deviceToken) {
      headers['X-Device-Token'] = deviceToken;
    }

    const response = await api.post<LoginResponse>('/auth/login', formData, { headers });
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  updateProfile: async (data: UserProfileUpdate): Promise<User> => {
    const response = await api.put('/auth/profile', data);
    return response.data;
  },

  changePassword: async (data: PasswordChange): Promise<void> => {
    await api.put('/auth/password', data);
  },

  getActivityHistory: async (): Promise<UserActivityHistory> => {
    const response = await api.get('/auth/activity');
    return response.data;
  },

  refreshToken: async (): Promise<TokenResponse> => {
    const response = await api.post('/auth/refresh');
    return response.data;
  },

  // Email Login (Magic Link)
  requestEmailLogin: async (email: string): Promise<EmailLoginResponse> => {
    const response = await api.post<EmailLoginResponse>('/auth/email-login/request', { email });
    return response.data;
  },

  verifyEmailCode: async (email: string, code: string): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>('/auth/email-login/verify', { email, code });
    return response.data;
  },

  checkEmailCodeStatus: async (email: string): Promise<EmailLoginStatus> => {
    const response = await api.get<EmailLoginStatus>('/auth/email-login/status', {
      params: { email },
    });
    return response.data;
  },

  uploadAvatar: async (file: File): Promise<{ message: string; avatar_url: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/auth/avatar', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // ============================================================================
  // Data Rights (Law 25 Compliance - Phase 2)
  // ============================================================================

  /**
   * Export user data (Law 25 compliance)
   * Returns a Blob for download
   */
  exportData: async (format: 'json' | 'csv' = 'json'): Promise<Blob> => {
    const response = await api.get(`/auth/export-data?format=${format}`, {
      responseType: 'blob',
    });
    return response.data;
  },

  /**
   * Delete user account (Law 25 compliance)
   */
  deleteAccount: async (data: {
    password: string;
    confirmation_text: string;
    delete_content: boolean;
  }): Promise<{
    message: string;
    deleted_at: string;
    data_deleted: boolean;
    content_anonymized: boolean;
  }> => {
    const response = await api.delete('/auth/account', { data });
    return response.data;
  },

  /**
   * Get consent status
   */
  getConsentStatus: async (): Promise<ConsentStatus> => {
    const response = await api.get('/auth/consent');
    return response.data;
  },

  /**
   * Update consent preferences
   */
  updateConsent: async (data: {
    marketing_consent?: boolean;
    accepts_terms?: boolean;
    accepts_privacy_policy?: boolean;
  }): Promise<ConsentStatus> => {
    const response = await api.put('/auth/consent', data);
    return response.data;
  },

  /**
   * Get consent history (Law 25 compliance)
   */
  getConsentHistory: async (): Promise<ConsentLogEntry[]> => {
    const response = await api.get('/auth/consent/history');
    return response.data;
  },

  // ============================================================================
  // Two-Factor Authentication (2FA)
  // ============================================================================

  /**
   * Initiate 2FA setup - returns secret and QR code URI
   */
  setup2FA: async (): Promise<TwoFactorSetupResponse> => {
    const response = await api.post<TwoFactorSetupResponse>('/auth/2fa/setup');
    return response.data;
  },

  /**
   * Verify 2FA setup with first code - enables 2FA and returns backup codes
   */
  verify2FASetup: async (code: string): Promise<TwoFactorVerifySetupResponse> => {
    const response = await api.post<TwoFactorVerifySetupResponse>('/auth/2fa/verify-setup', {
      code,
    });
    return response.data;
  },

  /**
   * Disable 2FA (requires password or email code)
   */
  disable2FA: async (request: TwoFactorDisableRequest): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>('/auth/2fa/disable', {
      data: request,
    });
    return response.data;
  },

  /**
   * Get current 2FA status
   */
  get2FAStatus: async (): Promise<TwoFactorStatusResponse> => {
    const response = await api.get<TwoFactorStatusResponse>('/auth/2fa/status');
    return response.data;
  },

  /**
   * Verify 2FA code during login (after receiving temp_token)
   * Supports device trust option (Law 25 compliant)
   */
  verify2FALogin: async (
    request: TwoFactorLoginWithTrustRequest
  ): Promise<TokenResponse | TokenWithDeviceToken> => {
    const response = await api.post<TokenResponse | TokenWithDeviceToken>(
      '/auth/2fa/verify',
      request
    );

    // If device token is returned, store it with device_id for "current device" detection
    const data = response.data as TokenWithDeviceToken;
    if (data.device_token && data.device_expires_at) {
      setDeviceToken(data.device_token, data.device_expires_at, data.device_id);
    }

    return response.data;
  },

  /**
   * Regenerate backup codes (requires password or email code)
   */
  regenerateBackupCodes: async (
    request: TwoFactorDisableRequest
  ): Promise<{ backup_codes: string[] }> => {
    const response = await api.post<{ backup_codes: string[] }>(
      '/auth/2fa/backup-codes/regenerate',
      request
    );
    return response.data;
  },

  /**
   * Get remaining backup codes count
   */
  getBackupCodesCount: async (): Promise<{ remaining: number }> => {
    const response = await api.get<{ remaining: number }>('/auth/2fa/backup-codes/count');
    return response.data;
  },

  // ============================================================================
  // Trusted Device Management (2FA Remember Device - Law 25 Compliance)
  // ============================================================================

  /**
   * Get all trusted devices for the current user
   */
  getTrustedDevices: async (): Promise<TrustedDeviceListResponse> => {
    const response = await api.get<TrustedDeviceListResponse>('/auth/2fa/devices');
    return response.data;
  },

  /**
   * Rename a trusted device
   */
  renameDevice: async (deviceId: number, newName: string): Promise<TrustedDevice> => {
    const response = await api.patch<TrustedDevice>(`/auth/2fa/devices/${deviceId}`, {
      device_name: newName,
    });
    return response.data;
  },

  /**
   * Revoke (delete) a specific trusted device
   */
  revokeDevice: async (deviceId: number): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/auth/2fa/devices/${deviceId}`);
    return response.data;
  },

  /**
   * Revoke all trusted devices for the current user
   */
  revokeAllDevices: async (): Promise<{ message: string; count: number }> => {
    const response = await api.delete<{ message: string; count: number }>('/auth/2fa/devices');
    // Also clear local device token since this device was likely revoked
    clearDeviceToken();
    return response.data;
  },

  /**
   * Clear local device token (for logout)
   */
  clearLocalDeviceToken: (): void => {
    clearDeviceToken();
  },

  // ============================================================================
  // Password Reset
  // ============================================================================

  /**
   * Request a password reset code
   * Returns same response whether email exists or not (prevents enumeration)
   */
  requestPasswordReset: async (email: string): Promise<PasswordResetRequestResponse> => {
    const response = await api.post<PasswordResetRequestResponse>('/auth/password-reset/request', {
      email,
    });
    return response.data;
  },

  /**
   * Verify password reset code and get reset token
   */
  verifyPasswordResetCode: async (
    email: string,
    code: string
  ): Promise<PasswordResetVerifyResponse> => {
    const response = await api.post<PasswordResetVerifyResponse>('/auth/password-reset/verify', {
      email,
      code,
    });
    return response.data;
  },

  /**
   * Complete password reset with new password
   */
  resetPassword: async (
    email: string,
    resetToken: string,
    newPassword: string
  ): Promise<PasswordResetCompleteResponse> => {
    const response = await api.post<PasswordResetCompleteResponse>('/auth/password-reset/reset', {
      email,
      reset_token: resetToken,
      new_password: newPassword,
    });
    return response.data;
  },
};

// Category APIs
export const categoryAPI = {
  getAll: async (): Promise<Category[]> => {
    const response = await api.get('/categories/');
    return response.data;
  },

  getOne: async (id: number): Promise<Category> => {
    const response = await api.get(`/categories/${id}`);
    return response.data;
  },
};

// Idea APIs
export const ideaAPI = {
  getLeaderboard: async (categoryId?: number, skip = 0, limit = 20): Promise<Idea[]> => {
    return startSpan(
      {
        name: 'fetchLeaderboard',
        op: 'http.client',
        attributes: {
          ...(categoryId !== undefined && { category_id: categoryId }),
          skip,
          limit,
        },
      },
      async () => {
        const params: Record<string, number | undefined> = { skip, limit };
        if (categoryId) params.category_id = categoryId;
        const response = await api.get('/ideas/leaderboard', { params });
        return response.data;
      }
    );
  },

  getMyIdeas: async (skip = 0, limit = 20): Promise<Idea[]> => {
    const response = await api.get('/ideas/my-ideas', { params: { skip, limit } });
    return response.data;
  },

  getOne: async (id: number): Promise<Idea> => {
    const response = await api.get(`/ideas/${id}`);
    return response.data;
  },

  create: async (data: IdeaCreate): Promise<Idea> => {
    // Capture current UI language if not explicitly provided
    const uiLanguage = i18n.language?.substring(0, 2) || 'fr';
    const language = data.language || uiLanguage;
    const response = await api.post('/ideas/', { ...data, language });
    return response.data;
  },

  update: async (id: number, data: Partial<IdeaCreate>): Promise<Idea> => {
    const response = await api.put(`/ideas/${id}`, data);
    return response.data;
  },

  delete: async (id: number, reason?: string): Promise<IdeaDeleteResponse> => {
    const response = await api.delete(`/ideas/${id}`, {
      data: reason ? { reason } : undefined,
    });
    return response.data;
  },

  checkSimilar: async (
    data: SimilarIdeaRequest,
    language: string = 'en',
    threshold: number = 0.3,
    limit: number = 5
  ): Promise<SimilarIdea[]> => {
    const response = await api.post('/ideas/check-similar', data, {
      params: { language, threshold, limit },
    });
    return response.data;
  },

  getQualitySignals: async (ideaId: number): Promise<QualitySignalsResponse> => {
    const response = await api.get<QualitySignalsResponse>(`/ideas/${ideaId}/quality-signals`);
    return response.data;
  },
};

// Vote APIs
export const voteAPI = {
  vote: async (ideaId: number, data: VoteCreate): Promise<void> => {
    await api.post(`/votes/${ideaId}`, data);
  },

  removeVote: async (ideaId: number): Promise<void> => {
    await api.delete(`/votes/${ideaId}`);
  },

  getQualities: async (ideaId: number): Promise<QualityType[]> => {
    const response = await api.get<QualityType[]>(`/votes/${ideaId}/qualities`);
    return response.data;
  },

  updateQualities: async (ideaId: number, qualities: QualityType[]): Promise<QualityType[]> => {
    const response = await api.put<QualityType[]>(`/votes/${ideaId}/qualities`, {
      quality_keys: qualities,
    });
    return response.data;
  },

  getMyVote: async (ideaId: number): Promise<VoteWithQualities | null> => {
    const response = await api.get<VoteWithQualities | null>(`/votes/${ideaId}/my-vote`);
    return response.data;
  },
};

// Comment sort order type
export type CommentSortOrder = 'relevance' | 'newest' | 'oldest' | 'most_liked';

// Comment APIs
export const commentAPI = {
  getForIdea: async (
    ideaId: number,
    skip = 0,
    limit = 50,
    sortBy: CommentSortOrder = 'relevance'
  ): Promise<Comment[]> => {
    const response = await api.get(`/comments/${ideaId}`, {
      params: { skip, limit, sort_by: sortBy },
    });
    return response.data;
  },

  create: async (ideaId: number, data: CommentCreate): Promise<Comment> => {
    // Capture current UI language if not explicitly provided
    const uiLanguage = i18n.language?.substring(0, 2) || 'fr';
    const language = data.language || uiLanguage;
    const response = await api.post(`/comments/${ideaId}`, { ...data, language });
    return response.data;
  },

  delete: async (commentId: number): Promise<void> => {
    await api.delete(`/comments/${commentId}`);
  },

  toggleLike: async (commentId: number): Promise<CommentLikeResponse> => {
    const response = await api.post<CommentLikeResponse>(`/comments/${commentId}/like`);
    return response.data;
  },
};

// Admin APIs
export const adminAPI = {
  getPendingIdeas: async (skip = 0, limit = 20): Promise<PendingIdeasResponse> => {
    const response = await api.get('/admin/ideas/pending', { params: { skip, limit } });
    return response.data;
  },

  moderateIdea: async (
    ideaId: number,
    status: 'approved' | 'rejected',
    adminComment?: string
  ): Promise<Idea> => {
    const response = await api.put(`/admin/ideas/${ideaId}/moderate`, {
      status,
      admin_comment: adminComment,
    });
    return response.data;
  },

  getAllComments: async (skip = 0, limit = 50): Promise<Comment[]> => {
    const response = await api.get('/admin/comments/all', { params: { skip, limit } });
    return response.data;
  },

  moderateComment: async (commentId: number, isModerated: boolean): Promise<void> => {
    await api.put(`/admin/comments/${commentId}/moderate`, { is_moderated: isModerated });
  },

  // Category Management
  getAllCategories: async (): Promise<CategoryStatistics[]> => {
    const response = await api.get('/admin/categories');
    return response.data;
  },

  createCategory: async (data: CategoryCreate): Promise<Category> => {
    const response = await api.post('/admin/categories', data);
    return response.data;
  },

  updateCategory: async (id: number, data: CategoryCreate): Promise<Category> => {
    const response = await api.put(`/admin/categories/${id}`, data);
    return response.data;
  },

  deleteCategory: async (id: number): Promise<void> => {
    await api.delete(`/admin/categories/${id}`);
  },

  getCategoryStatistics: async (id: number): Promise<CategoryStatistics> => {
    const response = await api.get(`/admin/categories/${id}/statistics`);
    return response.data;
  },

  // User Management
  getAllUsers: async (params?: UserFilterParams): Promise<UserListResponse> => {
    const response = await api.get('/admin/users', { params });
    return response.data;
  },

  getUserById: async (id: number): Promise<UserManagement> => {
    const response = await api.get(`/admin/users/${id}`);
    return response.data;
  },

  updateUser: async (id: number, data: UserUpdate): Promise<UserManagement> => {
    const response = await api.put(`/admin/users/${id}`, data);
    return response.data;
  },

  deleteUser: async (id: number): Promise<void> => {
    await api.delete(`/admin/users/${id}`);
  },

  getUserStatistics: async (id: number): Promise<UserStatistics> => {
    const response = await api.get(`/admin/users/${id}/statistics`);
    return response.data;
  },

  // Idea Deletion Management
  ideas: {
    /**
     * Delete any idea (admin only, requires reason)
     */
    delete: async (id: number, reason: string): Promise<IdeaDeleteResponse> => {
      const response = await api.delete(`/admin/ideas/${id}`, {
        data: { reason },
      });
      return response.data;
    },

    /**
     * Get list of deleted ideas (admin only)
     */
    getDeleted: async (params?: {
      skip?: number;
      limit?: number;
    }): Promise<DeletedIdeasListResponse> => {
      const response = await api.get('/admin/ideas/deleted', { params });
      return response.data;
    },

    /**
     * Restore a deleted idea (admin only)
     */
    restore: async (id: number): Promise<IdeaRestoreResponse> => {
      const response = await api.post(`/admin/ideas/${id}/restore`);
      return response.data;
    },

    /**
     * Get list of rejected ideas (admin only)
     */
    getRejected: async (params?: {
      skip?: number;
      limit?: number;
    }): Promise<RejectedIdeasListResponse> => {
      const response = await api.get('/admin/ideas/rejected', { params });
      return response.data;
    },
  },

  // Official Management
  officials: {
    /**
     * List all officials
     */
    getAll: async (): Promise<OfficialListItem[]> => {
      const response = await api.get<OfficialListItem[]>('/admin/officials');
      return response.data;
    },

    /**
     * Get pending official requests
     */
    getPendingRequests: async (): Promise<PendingOfficialRequest[]> => {
      const response = await api.get<PendingOfficialRequest[]>('/admin/officials/requests');
      return response.data;
    },

    /**
     * Grant official status to a user
     */
    grant: async (userId: number, officialTitle?: string): Promise<User> => {
      const response = await api.post<User>('/admin/officials/grant', {
        user_id: userId,
        official_title: officialTitle,
      });
      return response.data;
    },

    /**
     * Revoke official status from a user
     */
    revoke: async (userId: number): Promise<User> => {
      const response = await api.post<User>('/admin/officials/revoke', {
        user_id: userId,
      });
      return response.data;
    },

    /**
     * Update official's title
     */
    updateTitle: async (userId: number, title: string): Promise<User> => {
      const response = await api.put<User>(`/admin/officials/${userId}/title`, null, {
        params: { title },
      });
      return response.data;
    },

    /**
     * Reject a pending official request
     */
    rejectRequest: async (userId: number): Promise<void> => {
      await api.post(`/admin/officials/requests/${userId}/reject`);
    },
  },

  // Notifications (ntfy viewer)
  notifications: {
    /**
     * Get recent notifications from ntfy cache
     */
    getRecent: async (params?: {
      since?: string;
      limit?: number;
      language?: string;
    }): Promise<AdminNotification[]> => {
      const response = await api.get<AdminNotification[]>('/admin/notifications', {
        params,
      });
      return response.data;
    },

    /**
     * Get notification counts by topic
     */
    getCounts: async (): Promise<AdminNotificationCounts> => {
      const response = await api.get<AdminNotificationCounts>('/admin/notifications/counts');
      return response.data;
    },

    /**
     * Send a test notification to verify ntfy is working
     */
    sendTest: async (): Promise<{ success: boolean; message: string }> => {
      const response = await api.post<{ success: boolean; message: string }>(
        '/admin/notifications/test'
      );
      return response.data;
    },
  },

  // Diagnostics
  diagnostics: {
    /**
     * Check API health
     */
    checkHealth: async (): Promise<{ status: string }> => {
      const response = await api.get<{ status: string }>('/health');
      return response.data;
    },

    /**
     * Get platform info (root endpoint, not under /api)
     */
    getPlatformInfo: async (): Promise<{
      platform: string;
      version: string;
    }> => {
      const response = await axios.get<{ platform: string; version: string }>(
        `${getApiBaseUrl()}/`
      );
      return response.data;
    },

    /**
     * Test SMTP server connectivity
     */
    testSmtp: async (): Promise<{
      success: boolean;
      provider: string;
      host: string | null;
      port: number | null;
      message: string;
      details: string | null;
    }> => {
      const response = await api.post<{
        success: boolean;
        provider: string;
        host: string | null;
        port: number | null;
        message: string;
        details: string | null;
      }>('/admin/notifications/test-smtp');
      return response.data;
    },

    /**
     * Get database connectivity and table information
     */
    checkDatabase: async (): Promise<DatabaseDiagnosticsResponse> => {
      const response = await api.get<DatabaseDiagnosticsResponse>('/admin/diagnostics/database');
      return response.data;
    },

    /**
     * Get system resource usage (disk, docker, database size, memory)
     */
    getSystemResources: async (): Promise<SystemResourcesResponse> => {
      const response = await api.get<SystemResourcesResponse>('/admin/diagnostics/system');
      return response.data;
    },
  },

  // Security Audit (Phase 3)
  security: {
    /**
     * Get paginated list of security/login events
     */
    getEvents: async (params?: {
      skip?: number;
      limit?: number;
      event_type?: string;
      user_id?: number;
      since?: string;
    }): Promise<SecurityEventsResponse> => {
      const response = await api.get<SecurityEventsResponse>('/admin/security/events', {
        params,
      });
      return response.data;
    },

    /**
     * Get security summary statistics for dashboard
     */
    getSummary: async (): Promise<SecuritySummary> => {
      const response = await api.get<SecuritySummary>('/admin/security/summary');
      return response.data;
    },
  },
};

// ============================================================================
// Admin Roles API (Category Moderators)
// ============================================================================

export const adminRolesAPI = {
  /**
   * Get all category admin roles
   */
  getAll: async (): Promise<AdminRole[]> => {
    const response = await api.get<AdminRole[]>('/admin/roles');
    return response.data;
  },

  /**
   * Create a new category admin role
   */
  create: async (data: AdminRoleCreate): Promise<AdminRole> => {
    const response = await api.post<AdminRole>('/admin/roles', data);
    return response.data;
  },

  /**
   * Delete a category admin role
   */
  delete: async (roleId: number): Promise<void> => {
    await api.delete(`/admin/roles/${roleId}`);
  },
};

// Search APIs
export const searchAPI = {
  /**
   * Search ideas with full-text search
   */
  searchIdeas: async (params: SearchQueryParams): Promise<SearchResults> => {
    const queryParams = new URLSearchParams();
    queryParams.set('q', params.q);
    if (params.skip) queryParams.set('skip', params.skip.toString());
    if (params.limit) queryParams.set('limit', params.limit.toString());
    if (params.highlight !== undefined) queryParams.set('highlight', params.highlight.toString());

    // Add filters
    if (params.filters) {
      const { filters } = params;
      if (filters.category_id) queryParams.set('category_id', filters.category_id.toString());
      if (filters.category_ids?.length) {
        filters.category_ids.forEach((id) => queryParams.append('category_ids', id.toString()));
      }
      if (filters.status) queryParams.set('status', filters.status);
      if (filters.author_id) queryParams.set('author_id', filters.author_id.toString());
      if (filters.from_date) queryParams.set('from_date', filters.from_date);
      if (filters.to_date) queryParams.set('to_date', filters.to_date);
      if (filters.language) queryParams.set('language', filters.language);
      if (filters.tag_names?.length) {
        filters.tag_names.forEach((tag) => queryParams.append('tag_names', tag));
      }
      if (filters.min_score !== undefined)
        queryParams.set('min_score', filters.min_score.toString());
      if (filters.has_comments !== undefined)
        queryParams.set('has_comments', filters.has_comments.toString());
    }

    const response = await api.get(`/search/ideas?${queryParams.toString()}`);
    return response.data;
  },

  /**
   * Get autocomplete suggestions (ideas + tags)
   */
  getAutocomplete: async (query: string, limit = 5): Promise<AutocompleteResult> => {
    const response = await api.get('/search/autocomplete', {
      params: { q: query, limit },
    });
    return response.data;
  },

  /**
   * Get search suggestions (title matches)
   */
  getSuggestions: async (query: string, limit = 5): Promise<string[]> => {
    const response = await api.get('/search/suggestions', {
      params: { q: query, limit },
    });
    return response.data;
  },

  /**
   * Get search backend info
   */
  getSearchInfo: async (): Promise<{ backend: string; available: boolean }> => {
    const response = await api.get('/search/info');
    return response.data;
  },
};

// Analytics APIs
export const analyticsAPI = {
  getOverview: async (): Promise<OverviewMetrics> => {
    const response = await api.get('/admin/analytics/overview');
    return response.data;
  },

  getTrends: async (params: {
    start_date: string;
    end_date: string;
    granularity?: Granularity;
  }): Promise<TrendsResponse> => {
    const response = await api.get('/admin/analytics/trends', { params });
    return response.data;
  },

  getCategoriesAnalytics: async (): Promise<CategoriesAnalyticsResponse> => {
    const response = await api.get('/admin/analytics/categories');
    return response.data;
  },

  getTopContributors: async (params?: {
    type?: ContributorType;
    limit?: number;
  }): Promise<TopContributorsResponse> => {
    const response = await api.get('/admin/analytics/top-contributors', { params });
    return response.data;
  },

  refreshCache: async (cacheKey?: string): Promise<{ message: string; key: string }> => {
    const response = await api.post('/admin/analytics/refresh', null, {
      params: cacheKey ? { cache_key: cacheKey } : undefined,
    });
    return response.data;
  },

  exportData: async (params: {
    data_type: 'overview' | 'ideas' | 'users' | 'categories';
    start_date?: string;
    end_date?: string;
  }): Promise<Blob> => {
    const response = await api.get('/admin/analytics/export', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  getQualityAnalytics: async (): Promise<QualityAnalyticsResponse> => {
    const response = await api.get('/admin/analytics/qualities');
    return response.data;
  },

  /**
   * Get weighted score analysis for a specific idea
   */
  getWeightedScore: async (ideaId: number): Promise<WeightedScoreResponse> => {
    const response = await api.get<WeightedScoreResponse>(
      `/admin/analytics/weighted-scores/${ideaId}`
    );
    return response.data;
  },

  /**
   * Get list of ideas with score anomalies (high divergence between public and weighted scores)
   */
  getScoreAnomalies: async (threshold?: number): Promise<ScoreAnomaliesResponse> => {
    const response = await api.get<ScoreAnomaliesResponse>('/admin/analytics/score-anomalies', {
      params: threshold ? { threshold } : undefined,
    });
    return response.data;
  },
};

// ============================================================================
// Moderation API
// ============================================================================

export const moderationAPI = {
  // Flags
  createFlag: async (data: FlagCreate): Promise<FlagResponse> => {
    const response = await api.post<FlagResponse>('/flags', data);
    return response.data;
  },

  getMyFlags: async (skip = 0, limit = 50): Promise<FlagResponse[]> => {
    const response = await api.get<FlagResponse[]>('/flags/my-flags', {
      params: { skip, limit },
    });
    return response.data;
  },

  retractFlag: async (flagId: number): Promise<void> => {
    await api.delete(`/flags/${flagId}`);
  },

  checkFlagStatus: async (
    contentType: ContentType,
    contentId: number
  ): Promise<FlagCheckResponse> => {
    const response = await api.get<FlagCheckResponse>(`/flags/check/${contentType}/${contentId}`);
    return response.data;
  },

  // Appeals
  submitAppeal: async (data: AppealCreate): Promise<AppealResponse> => {
    const response = await api.post<AppealResponse>('/appeals', data);
    return response.data;
  },

  getMyAppeals: async (skip = 0, limit = 50): Promise<AppealResponse[]> => {
    const response = await api.get<AppealResponse[]>('/appeals/my-appeals', {
      params: { skip, limit },
    });
    return response.data;
  },
};

// ============================================================================
// Admin Moderation API
// ============================================================================

export const adminModerationAPI = {
  // Moderation Queue
  getQueue: async (
    contentType?: ContentType,
    reason?: FlagReason,
    skip = 0,
    limit = 50
  ): Promise<ModerationQueueResponse> => {
    const response = await api.get<ModerationQueueResponse>('/admin/moderation/queue', {
      params: { content_type: contentType, reason, skip, limit },
    });
    return response.data;
  },

  getFlagsForContent: async (
    contentType: ContentType,
    contentId: number
  ): Promise<FlagWithReporter[]> => {
    const response = await api.get<FlagWithReporter[]>(
      `/admin/moderation/flags/${contentType}/${contentId}`
    );
    return response.data;
  },

  reviewFlags: async (
    flagIds: number[],
    action: 'dismiss' | 'action',
    reviewNotes?: string,
    issuePenalty = false,
    penaltyType?: PenaltyType,
    penaltyReason?: string
  ): Promise<{ action: string; flags_updated: number }> => {
    const response = await api.post('/admin/moderation/review', {
      flag_ids: flagIds,
      action,
      review_notes: reviewNotes,
      issue_penalty: issuePenalty,
      penalty_type: penaltyType,
      penalty_reason: penaltyReason,
    });
    return response.data;
  },

  getFlaggedUsers: async (
    skip = 0,
    limit = 50
  ): Promise<{ users: FlaggedUserSummary[]; total: number }> => {
    const response = await api.get('/admin/moderation/flagged-users', {
      params: { skip, limit },
    });
    return response.data;
  },

  getStats: async (): Promise<ModerationStats> => {
    const response = await api.get<ModerationStats>('/admin/moderation/stats');
    return response.data;
  },

  // Penalties
  issuePenalty: async (
    userId: number,
    penaltyType: PenaltyType,
    reason: string,
    relatedFlagIds?: number[],
    bulkDeleteContent = false
  ): Promise<PenaltyResponse> => {
    const response = await api.post<PenaltyResponse>('/admin/moderation/penalties', {
      user_id: userId,
      penalty_type: penaltyType,
      reason,
      related_flag_ids: relatedFlagIds,
      bulk_delete_content: bulkDeleteContent,
    });
    return response.data;
  },

  getAllPenalties: async (
    penaltyType?: PenaltyType,
    skip = 0,
    limit = 50
  ): Promise<{ penalties: PenaltyResponse[]; total: number }> => {
    const response = await api.get('/admin/moderation/penalties', {
      params: { penalty_type: penaltyType, skip, limit },
    });
    return response.data;
  },

  getUserPenalties: async (userId: number, includeExpired = true): Promise<PenaltyResponse[]> => {
    const response = await api.get<PenaltyResponse[]>(
      `/admin/moderation/penalties/user/${userId}`,
      { params: { include_expired: includeExpired } }
    );
    return response.data;
  },

  revokePenalty: async (penaltyId: number, reason: string): Promise<PenaltyResponse> => {
    const response = await api.put<PenaltyResponse>(
      `/admin/moderation/penalties/${penaltyId}/revoke`,
      { reason }
    );
    return response.data;
  },

  // Appeals
  getPendingAppeals: async (
    skip = 0,
    limit = 50
  ): Promise<{ appeals: AppealResponse[]; total: number }> => {
    const response = await api.get('/admin/moderation/appeals', {
      params: { skip, limit },
    });
    return response.data;
  },

  reviewAppeal: async (
    appealId: number,
    action: 'approve' | 'reject',
    reviewNotes: string
  ): Promise<AppealResponse> => {
    const response = await api.put<AppealResponse>(`/admin/moderation/appeals/${appealId}`, {
      action,
      review_notes: reviewNotes,
    });
    return response.data;
  },

  // Admin Notes
  getUserNotes: async (userId: number): Promise<AdminNote[]> => {
    const response = await api.get<AdminNote[]>(`/admin/moderation/notes/user/${userId}`);
    return response.data;
  },

  addUserNote: async (userId: number, content: string): Promise<AdminNote> => {
    const response = await api.post<AdminNote>(`/admin/moderation/notes/user/${userId}`, {
      content,
    });
    return response.data;
  },

  updateNote: async (noteId: number, content: string): Promise<AdminNote> => {
    const response = await api.put<AdminNote>(`/admin/moderation/notes/${noteId}`, { content });
    return response.data;
  },

  deleteNote: async (noteId: number): Promise<void> => {
    await api.delete(`/admin/moderation/notes/${noteId}`);
  },

  // Keyword Watchlist
  getWatchlist: async (activeOnly = false): Promise<KeywordEntry[]> => {
    const response = await api.get<KeywordEntry[]>('/admin/moderation/watchlist', {
      params: { active_only: activeOnly },
    });
    return response.data;
  },

  addKeyword: async (
    keyword: string,
    isRegex = false,
    autoFlagReason: FlagReason = 'spam'
  ): Promise<KeywordEntry> => {
    const response = await api.post<KeywordEntry>('/admin/moderation/watchlist', {
      keyword,
      is_regex: isRegex,
      auto_flag_reason: autoFlagReason,
    });
    return response.data;
  },

  updateKeyword: async (
    keywordId: number,
    updates: {
      is_regex?: boolean;
      auto_flag_reason?: FlagReason;
      is_active?: boolean;
    }
  ): Promise<KeywordEntry> => {
    const response = await api.put<KeywordEntry>(
      `/admin/moderation/watchlist/${keywordId}`,
      updates
    );
    return response.data;
  },

  deleteKeyword: async (keywordId: number): Promise<void> => {
    await api.delete(`/admin/moderation/watchlist/${keywordId}`);
  },

  testKeyword: async (keyword: string, testText: string): Promise<boolean> => {
    const response = await api.post<{ matches: boolean }>('/admin/moderation/watchlist/test', {
      keyword,
      test_text: testText,
    });
    return response.data.matches;
  },

  // Pending Comments
  getPendingComments: async (skip = 0, limit = 50): Promise<PendingComment[]> => {
    const response = await api.get<PendingComment[]>('/admin/comments/pending-approval', {
      params: { skip, limit },
    });
    return response.data;
  },

  approveComment: async (commentId: number): Promise<void> => {
    await api.post(`/admin/comments/${commentId}/approve`);
  },

  rejectComment: async (commentId: number, reason?: string): Promise<void> => {
    await api.delete(`/admin/comments/${commentId}/reject`, {
      params: { reason },
    });
  },
};

// ============================================================================
// Officials API (for officials/admin dashboard)
// ============================================================================

export const officialsAPI = {
  // Analytics
  getOverview: async (): Promise<OfficialsQualityOverview> => {
    const response = await api.get<OfficialsQualityOverview>('/officials/analytics/overview');
    return response.data;
  },

  getTopIdeas: async (qualityKey?: string, limit = 10): Promise<OfficialsTopIdeaByQuality[]> => {
    const response = await api.get<OfficialsTopIdeaByQuality[]>('/officials/analytics/top-ideas', {
      params: { quality_key: qualityKey, limit },
    });
    return response.data;
  },

  getCategoryBreakdown: async (): Promise<OfficialsCategoryQualityBreakdown[]> => {
    const response = await api.get<OfficialsCategoryQualityBreakdown[]>(
      '/officials/analytics/categories'
    );
    return response.data;
  },

  getTrends: async (days = 30): Promise<OfficialsTimeSeriesPoint[]> => {
    const response = await api.get<OfficialsTimeSeriesPoint[]>('/officials/analytics/trends', {
      params: { days },
    });
    return response.data;
  },

  // Ideas with quality stats
  getIdeas: async (params: {
    quality_filter?: string;
    min_quality_count?: number;
    category_id?: number;
    sort_by?: 'quality_count' | 'score' | 'created_at';
    sort_order?: 'asc' | 'desc';
    skip?: number;
    limit?: number;
  }): Promise<OfficialsIdeasWithQualityResponse> => {
    const response = await api.get<OfficialsIdeasWithQualityResponse>('/officials/ideas', {
      params,
    });
    return response.data;
  },

  // Single idea detail with quality breakdown
  getIdeaDetail: async (ideaId: number): Promise<OfficialsIdeaDetail> => {
    const response = await api.get<OfficialsIdeaDetail>(`/officials/ideas/${ideaId}`);
    return response.data;
  },

  // Export
  exportIdeasCSV: (params: {
    quality_filter?: string;
    min_quality_count?: number;
    category_id?: number;
  }): void => {
    const queryString = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString();
    const token = localStorage.getItem('token');
    const url = `${API_URL}/officials/export/ideas.csv?${queryString}`;
    // Open in new tab with auth header via fetch + blob
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `ideas_export_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        window.URL.revokeObjectURL(blobUrl);
      });
  },

  exportAnalyticsCSV: (): void => {
    const token = localStorage.getItem('token');
    const url = `${API_URL}/officials/export/analytics.csv`;
    fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.blob())
      .then((blob) => {
        const blobUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = blobUrl;
        a.download = `analytics_export_${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        window.URL.revokeObjectURL(blobUrl);
      });
  },
};

// Legal content API (Terms of Service, Privacy Policy)
interface LegalDocument {
  version: string;
  last_updated: string;
  html_content: string;
}

export const legalAPI = {
  getDocument: async (
    documentType: 'terms' | 'privacy',
    locale: string
  ): Promise<LegalDocument> => {
    const response = await api.get<LegalDocument>(`/legal/${documentType}/${locale}`);
    return response.data;
  },
};

// =============================================================================
// Contact Form API
// =============================================================================

export type ContactSubject =
  | 'general'
  | 'account'
  | 'idea'
  | 'bug'
  | 'feedback'
  | 'privacy'
  | 'other';

export interface ContactFormRequest {
  name: string;
  email: string;
  subject: ContactSubject;
  message: string;
  language: 'en' | 'fr' | 'es';
}

export interface ContactFormResponse {
  success: boolean;
  message: string;
}

export const contactAPI = {
  /**
   * Submit a contact form message.
   * Sends email to admin and confirmation to user.
   */
  submit: async (form: ContactFormRequest): Promise<ContactFormResponse> => {
    const response = await api.post<ContactFormResponse>('/contact', form);
    return response.data;
  },
};

// =============================================================================
// Error Reporting API
// =============================================================================

export const errorAPI = {
  /**
   * Report a critical frontend error for admin notification.
   * Fire-and-forget - failures are logged but don't block.
   */
  reportCritical: async (error: {
    error_type: string;
    error_message: string;
    url: string;
    sentry_event_id?: string;
  }): Promise<void> => {
    try {
      await api.post('/errors/report', error);
    } catch {
      // Silent fail - don't block error handling
      console.warn('Failed to report error to admin');
    }
  },
};

// =============================================================================
// Share Tracking API
// =============================================================================

export const shareAPI = {
  /**
   * Record a share event for analytics tracking.
   * Fire-and-forget - failures are logged but don't block.
   */
  recordShare: async (ideaId: number, platform: SharePlatform): Promise<void> => {
    await api.post(`/shares/${ideaId}`, {
      platform,
      referrer_url: typeof window !== 'undefined' ? window.location.href : undefined,
    });
  },

  /**
   * Get share analytics for an idea.
   */
  getShareAnalytics: async (ideaId: number): Promise<ShareAnalyticsResponse> => {
    const response = await api.get<ShareAnalyticsResponse>(`/shares/${ideaId}/analytics`);
    return response.data;
  },
};

// =============================================================================
// Beta Access API (Security Hardening Phase 1)
// =============================================================================

export interface BetaVerifyResponse {
  success: boolean;
}

export interface BetaStatusResponse {
  beta_mode_enabled: boolean;
  has_access: boolean;
}

export const betaAPI = {
  /**
   * Verify beta password server-side.
   * Sets an httpOnly cookie on success for persistent access.
   */
  verify: async (password: string): Promise<BetaVerifyResponse> => {
    const response = await api.post<BetaVerifyResponse>('/beta/verify', { password });
    return response.data;
  },

  /**
   * Check beta access status (via cookie).
   */
  getStatus: async (): Promise<BetaStatusResponse> => {
    const response = await api.get<BetaStatusResponse>('/beta/status');
    return response.data;
  },
};

export default api;
