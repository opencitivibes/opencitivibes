'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { SearchResultItem } from './SearchResultItem';
import api from '@/lib/api';
import type { SearchResults as SearchResultsType, TagWithCount } from '@/types';

interface SearchResultsProps {
  results: SearchResultsType | null;
  isLoading: boolean;
  query: string;
  onLoadMore?: () => void;
  hasMore?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

export function SearchResults({
  results,
  isLoading,
  query,
  onLoadMore,
  hasMore = false,
  error = null,
  onRetry,
}: SearchResultsProps) {
  const { t } = useTranslation();
  const router = useRouter();
  const [popularTags, setPopularTags] = useState<TagWithCount[]>([]);

  // Load popular tags for suggestions
  useEffect(() => {
    const loadTags = async () => {
      try {
        const response = await api.get('/tags/popular?limit=6&min_ideas=1');
        setPopularTags(response.data);
      } catch {
        // Silently fail - suggestions are optional
      }
    };
    loadTags();
  }, []);

  const handleTagClick = (tagName: string) => {
    router.push(`/search?q=${encodeURIComponent(tagName)}`);
  };

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-6 w-48 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-100 dark:border-gray-700 animate-pulse"
          >
            <div className="flex justify-between items-start mb-4">
              <div className="flex-1">
                <div className="h-6 w-3/4 bg-gray-200 dark:bg-gray-700 rounded mb-3" />
                <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
              </div>
              <div className="w-16">
                <div className="h-10 w-10 bg-gray-200 dark:bg-gray-700 rounded mx-auto mb-1" />
                <div className="h-3 w-10 bg-gray-200 dark:bg-gray-700 rounded mx-auto" />
              </div>
            </div>
            <div className="space-y-2 mb-4">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full" />
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-4/6" />
            </div>
            <div className="flex gap-2 mb-4">
              <div className="h-6 w-16 bg-gray-200 dark:bg-gray-700 rounded-full" />
              <div className="h-6 w-20 bg-gray-200 dark:bg-gray-700 rounded-full" />
            </div>
            <div className="flex justify-between">
              <div className="h-4 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  // No query yet
  if (!query || query.length < 2) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-16 w-16 text-gray-300 dark:text-gray-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <p className="mt-4 text-gray-500 dark:text-gray-400">{t('search.enterQuery')}</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-16 w-16 text-warning-500 dark:text-warning-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <p className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
          {t('search.searchError')}
        </p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            {t('search.retrySearch')}
          </button>
        )}
      </div>
    );
  }

  // No results - improved UX with suggestions
  if (!results || results.results.length === 0) {
    return (
      <div className="text-center py-12">
        <svg
          className="mx-auto h-16 w-16 text-gray-300 dark:text-gray-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
          {t('search.noResultsTitle', { query })}
        </h3>
        <p className="mt-2 text-gray-500 dark:text-gray-400 max-w-md mx-auto">
          {t('search.noResultsHint')}
        </p>

        {/* Popular tags suggestions */}
        {popularTags.length > 0 && (
          <div className="mt-6 space-y-3">
            <p className="text-sm font-medium text-gray-600 dark:text-gray-300">
              {t('search.tryAlternatives')}
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {popularTags.map((tag) => (
                <button
                  key={tag.id}
                  type="button"
                  onClick={() => handleTagClick(tag.display_name)}
                  className="px-3 py-1.5 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded-full text-sm font-medium hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                >
                  #{tag.display_name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Browse all link */}
        <div className="mt-6">
          <Link
            href="/"
            className="text-primary-600 dark:text-primary-400 hover:underline text-sm font-medium"
          >
            {t('search.browseAll')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Results count */}
      <div className="flex items-center justify-between">
        <p className="text-gray-600 dark:text-gray-300">
          {t('search.results', { count: results.total, query })}
        </p>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {t('search.backend')}: {results.search_backend}
        </span>
      </div>

      {/* Results list */}
      <div className="space-y-4">
        {results.results.map((result) => (
          <SearchResultItem key={result.idea.id} result={result} />
        ))}
      </div>

      {/* Load more */}
      {hasMore && onLoadMore && (
        <div className="text-center pt-4">
          <button
            type="button"
            onClick={onLoadMore}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            {t('ideas.loadMore')}
          </button>
        </div>
      )}
    </div>
  );
}

export default SearchResults;
