import useSWR, { SWRConfiguration } from 'swr';
import {
  categoryAPI,
  ideaAPI,
  commentAPI,
  searchAPI,
  analyticsAPI,
  adminAPI,
  adminModerationAPI,
} from '@/lib/api';
import type {
  Idea,
  Category,
  Comment,
  SearchQueryParams,
  SearchResults,
  PendingIdeasResponse,
} from '@/types';
import type {
  ContentType,
  FlagReason,
  ModerationQueueResponse,
  ModerationStats,
  PendingComment,
} from '@/types/moderation';

// Default SWR config with sensible cache settings
const defaultConfig: SWRConfiguration = {
  revalidateOnFocus: false,
  revalidateIfStale: true,
  dedupingInterval: 2000,
};

// ============================================================================
// Category Hooks
// ============================================================================

export function useCategories(config?: SWRConfiguration) {
  return useSWR<Category[]>('categories', () => categoryAPI.getAll(), {
    ...defaultConfig,
    // Categories rarely change, cache for longer
    revalidateOnFocus: false,
    refreshInterval: 5 * 60 * 1000, // 5 minutes
    ...config,
  });
}

export function useCategory(id: number | undefined, config?: SWRConfiguration) {
  return useSWR<Category>(id ? `category-${id}` : null, () => categoryAPI.getOne(id!), {
    ...defaultConfig,
    ...config,
  });
}

// ============================================================================
// Idea Hooks
// ============================================================================

export function useLeaderboard(
  categoryId?: number,
  skip = 0,
  limit = 20,
  config?: SWRConfiguration
) {
  const key = categoryId
    ? `leaderboard-${categoryId}-${skip}-${limit}`
    : `leaderboard-${skip}-${limit}`;

  return useSWR<Idea[]>(key, () => ideaAPI.getLeaderboard(categoryId, skip, limit), {
    ...defaultConfig,
    ...config,
  });
}

export function useIdea(id: number | undefined, config?: SWRConfiguration) {
  return useSWR<Idea>(id ? `idea-${id}` : null, () => ideaAPI.getOne(id!), {
    ...defaultConfig,
    ...config,
  });
}

export function useMyIdeas(skip = 0, limit = 20, config?: SWRConfiguration) {
  return useSWR<Idea[]>(`my-ideas-${skip}-${limit}`, () => ideaAPI.getMyIdeas(skip, limit), {
    ...defaultConfig,
    ...config,
  });
}

// ============================================================================
// Comment Hooks
// ============================================================================

export function useComments(
  ideaId: number | undefined,
  skip = 0,
  limit = 50,
  config?: SWRConfiguration
) {
  return useSWR<Comment[]>(
    ideaId ? `comments-${ideaId}-${skip}-${limit}` : null,
    () => commentAPI.getForIdea(ideaId!, skip, limit),
    {
      ...defaultConfig,
      ...config,
    }
  );
}

// ============================================================================
// Search Hooks
// ============================================================================

export function useSearch(params: SearchQueryParams | null, config?: SWRConfiguration) {
  const key = params ? `search-${JSON.stringify(params)}` : null;

  return useSWR<SearchResults>(key, () => searchAPI.searchIdeas(params!), {
    ...defaultConfig,
    // Search results can be cached but should be fresh
    dedupingInterval: 5000,
    ...config,
  });
}

export function useAutocomplete(query: string, limit = 5, config?: SWRConfiguration) {
  // Only trigger when query has at least 2 characters
  const shouldFetch = query.length >= 2;

  return useSWR(
    shouldFetch ? `autocomplete-${query}-${limit}` : null,
    () => searchAPI.getAutocomplete(query, limit),
    {
      ...defaultConfig,
      dedupingInterval: 1000,
      ...config,
    }
  );
}

// ============================================================================
// Analytics Hooks (Admin)
// ============================================================================

export function useAnalyticsOverview(config?: SWRConfiguration) {
  return useSWR('analytics-overview', () => analyticsAPI.getOverview(), {
    ...defaultConfig,
    // Analytics can be stale for a bit longer
    refreshInterval: 60 * 1000, // 1 minute
    ...config,
  });
}

export function useAnalyticsTrends(
  startDate: string,
  endDate: string,
  granularity?: 'day' | 'week' | 'month',
  config?: SWRConfiguration
) {
  const key = `analytics-trends-${startDate}-${endDate}-${granularity}`;

  return useSWR(
    key,
    () => analyticsAPI.getTrends({ start_date: startDate, end_date: endDate, granularity }),
    {
      ...defaultConfig,
      ...config,
    }
  );
}

export function useCategoriesAnalytics(config?: SWRConfiguration) {
  return useSWR('analytics-categories', () => analyticsAPI.getCategoriesAnalytics(), {
    ...defaultConfig,
    refreshInterval: 60 * 1000,
    ...config,
  });
}

// ============================================================================
// Admin Hooks
// ============================================================================

export function usePendingIdeas(skip = 0, limit = 20, config?: SWRConfiguration) {
  return useSWR<PendingIdeasResponse>(
    `pending-ideas-${skip}-${limit}`,
    () => adminAPI.getPendingIdeas(skip, limit),
    {
      ...defaultConfig,
      ...config,
    }
  );
}

export function useDeletedIdeas(skip = 0, limit = 20, config?: SWRConfiguration) {
  return useSWR(
    `deleted-ideas-${skip}-${limit}`,
    () => adminAPI.ideas.getDeleted({ skip, limit }),
    {
      ...defaultConfig,
      ...config,
    }
  );
}

// ============================================================================
// Moderation Hooks
// ============================================================================

export function useModerationQueue(
  contentType?: ContentType,
  reason?: FlagReason,
  skip = 0,
  limit = 50,
  config?: SWRConfiguration
) {
  const key = `moderation-queue-${contentType}-${reason}-${skip}-${limit}`;

  return useSWR<ModerationQueueResponse>(
    key,
    () => adminModerationAPI.getQueue(contentType, reason, skip, limit),
    {
      ...defaultConfig,
      ...config,
    }
  );
}

export function useModerationStats(config?: SWRConfiguration) {
  return useSWR<ModerationStats>('moderation-stats', () => adminModerationAPI.getStats(), {
    ...defaultConfig,
    refreshInterval: 30 * 1000, // 30 seconds
    ...config,
  });
}

export function usePendingComments(skip = 0, limit = 50, config?: SWRConfiguration) {
  return useSWR<PendingComment[]>(
    `pending-comments-${skip}-${limit}`,
    () => adminModerationAPI.getPendingComments(skip, limit),
    {
      ...defaultConfig,
      ...config,
    }
  );
}

// ============================================================================
// Mutation Helpers
// ============================================================================

// Helper to invalidate related caches after mutations
export function getLeaderboardKey(categoryId?: number, skip = 0, limit = 20) {
  return categoryId ? `leaderboard-${categoryId}-${skip}-${limit}` : `leaderboard-${skip}-${limit}`;
}

export function getIdeaKey(id: number) {
  return `idea-${id}`;
}

export function getCommentsKey(ideaId: number, skip = 0, limit = 50) {
  return `comments-${ideaId}-${skip}-${limit}`;
}
