'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { Card } from '@/components/Card';
import api from '@/lib/api';
import type { TagWithCount } from '@/types';

// Get tag size class based on popularity ratio
const getTagSize = (count: number, maxCount: number): string => {
  if (maxCount === 0) return 'text-sm font-medium';
  const ratio = count / maxCount;
  if (ratio > 0.7) return 'text-base font-semibold';
  if (ratio > 0.4) return 'text-sm font-medium';
  return 'text-xs font-normal';
};

export default function PopularTags() {
  const { t } = useTranslation();
  const [tags, setTags] = useState<TagWithCount[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadPopularTags = async () => {
      try {
        setIsLoading(true);
        const response = await api.get('/tags/popular?limit=15&min_ideas=1');
        setTags(response.data);
      } catch (err) {
        console.error('Error loading popular tags:', err);
        setError(t('tags.loadError', 'Failed to load tags'));
      } finally {
        setIsLoading(false);
      }
    };

    loadPopularTags();
  }, [t]);

  if (isLoading) {
    return (
      <Card>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {t('tags.popularTags', 'Popular Tags')}
        </h3>
        <div className="animate-pulse space-y-2">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded"></div>
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
        </div>
      </Card>
    );
  }

  if (error || tags.length === 0) {
    return null;
  }

  const maxCount = Math.max(...tags.map((t) => t.idea_count));

  return (
    <Card>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
        <svg
          className="w-5 h-5 text-primary-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
          />
        </svg>
        {t('tags.popularTags', 'Popular Tags')}
      </h3>
      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <Link
            key={tag.id}
            href={`/tags/${encodeURIComponent(tag.name)}`}
            className={`
              px-3 py-1.5 bg-primary-50 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded-full
              hover:bg-primary-100 dark:hover:bg-primary-900/60 transition-colors
              ${getTagSize(tag.idea_count, maxCount)}
            `}
          >
            {tag.display_name}
            <span className="ml-1.5 text-primary-400 dark:text-primary-500">
              ({tag.idea_count})
            </span>
          </Link>
        ))}
      </div>
    </Card>
  );
}
