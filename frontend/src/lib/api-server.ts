/**
 * Server-side API utilities for Next.js Server Components
 *
 * Use this module for fetching data in Server Components (page.tsx, layout.tsx, etc.)
 * For client-side data fetching, use: import { ideaAPI, tagAPI } from '@/lib/api'
 *
 * Benefits:
 * - Typed responses with TypeScript generics
 * - Consistent error handling
 * - Next.js caching with revalidation options
 * - Centralized API URL management
 */

import type { Idea, Tag, TagStatistics } from '@/types';

// Use internal URL for server-side rendering (Docker service name), fallback to public URL
const API_BASE_URL =
  process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

interface FetchOptions {
  revalidate?: number | false;
  tags?: string[];
}

/**
 * Generic fetch wrapper with error handling and typing
 */
async function fetchAPI<T>(endpoint: string, options: FetchOptions = {}): Promise<T | null> {
  const { revalidate = 60, tags } = options;

  try {
    const fetchOptions: RequestInit & { next?: { revalidate?: number | false; tags?: string[] } } =
      {
        next: {},
      };

    if (revalidate !== undefined) {
      fetchOptions.next!.revalidate = revalidate;
    }

    if (tags) {
      fetchOptions.next!.tags = tags;
    }

    const res = await fetch(`${API_BASE_URL}${endpoint}`, fetchOptions);

    if (!res.ok) {
      return null;
    }

    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

/**
 * Server-side Idea API
 */
export const serverIdeaAPI = {
  /**
   * Get a single idea by ID
   */
  async getOne(id: string | number, options?: FetchOptions): Promise<Idea | null> {
    return fetchAPI<Idea>(`/ideas/${id}`, {
      revalidate: 60,
      tags: [`idea-${id}`],
      ...options,
    });
  },

  /**
   * Get leaderboard ideas (for static generation)
   */
  async getLeaderboard(limit = 50, options?: FetchOptions): Promise<Idea[]> {
    const result = await fetchAPI<Idea[]>(`/ideas/leaderboard?limit=${limit}`, {
      revalidate: 300,
      tags: ['ideas-leaderboard'],
      ...options,
    });
    return result || [];
  },

  /**
   * Get ideas by category
   */
  async getByCategory(
    categoryId: number,
    skip = 0,
    limit = 20,
    options?: FetchOptions
  ): Promise<Idea[]> {
    const result = await fetchAPI<Idea[]>(
      `/ideas/leaderboard?category_id=${categoryId}&skip=${skip}&limit=${limit}`,
      {
        revalidate: 60,
        tags: [`category-${categoryId}-ideas`],
        ...options,
      }
    );
    return result || [];
  },
};

/**
 * Server-side Tag API
 */
export const serverTagAPI = {
  /**
   * Get tag by name
   */
  async getByName(name: string, options?: FetchOptions): Promise<Tag | null> {
    return fetchAPI<Tag>(`/tags/by-name/${encodeURIComponent(name)}`, {
      revalidate: 300,
      tags: [`tag-${name}`],
      ...options,
    });
  },

  /**
   * Get tag statistics
   */
  async getStatistics(tagId: number, options?: FetchOptions): Promise<TagStatistics | null> {
    return fetchAPI<TagStatistics>(`/tags/${tagId}/statistics`, {
      revalidate: 300,
      tags: [`tag-${tagId}-stats`],
      ...options,
    });
  },

  /**
   * Get tag statistics by name (combines getByName + getStatistics)
   */
  async getStatsByName(name: string, options?: FetchOptions): Promise<TagStatistics | null> {
    const tag = await this.getByName(name, options);
    if (!tag) return null;
    return this.getStatistics(tag.id, options);
  },
};

/**
 * Server-side Category API
 */
export const serverCategoryAPI = {
  /**
   * Get all categories
   */
  async getAll(options?: FetchOptions): Promise<{ id: number; slug: string }[]> {
    const result = await fetchAPI<{ id: number; slug: string }[]>('/categories', {
      revalidate: 3600, // Categories rarely change
      tags: ['categories'],
      ...options,
    });
    return result || [];
  },
};
