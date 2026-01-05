'use client';

import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import DOMPurify from 'dompurify';
import TagBadge from '@/components/TagBadge';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import type { SearchResultItem as ResultType } from '@/types';

interface SearchResultItemProps {
  result: ResultType;
}

export function SearchResultItem({ result }: SearchResultItemProps) {
  const { idea, highlights } = result;
  const { t } = useTranslation();
  const { getField, formatDate, getDisplayName } = useLocalizedField();

  const categoryName = getField(
    { name_fr: idea.category_name_fr, name_en: idea.category_name_en },
    'name'
  );

  // Render highlighted text safely - only allow <mark> tags using DOMPurify
  const renderHighlight = (html: string | undefined, fallback: string) => {
    if (!html) return <span>{fallback}</span>;
    // First strip all HTML tags except <mark> and </mark> to handle raw HTML in content
    const strippedHtml = html.replace(/<(?!\/?mark\b)[^>]*>/gi, '');
    const sanitized = DOMPurify.sanitize(strippedHtml, {
      ALLOWED_TAGS: ['mark'],
      ALLOWED_ATTR: [],
      KEEP_CONTENT: true,
    });
    return <span dangerouslySetInnerHTML={{ __html: sanitized }} />;
  };

  return (
    <Link href={`/ideas/${idea.id}`}>
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-100 dark:border-gray-700 hover:shadow-xl hover:-translate-y-1 hover:border-primary-200 dark:hover:border-primary-600 transition-all duration-200 cursor-pointer">
        {/* Header */}
        <div className="flex justify-between items-start mb-3">
          <div className="flex-1">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2 [&>span>mark]:bg-yellow-200 dark:[&>span>mark]:bg-yellow-500/30 [&>span>mark]:px-0.5 [&>span>mark]:rounded">
              {renderHighlight(highlights?.title, idea.title)}
            </h3>
            <div className="flex flex-wrap gap-2 text-sm text-gray-600 dark:text-gray-300">
              <span className="px-2 py-1 bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded">
                {categoryName}
              </span>
            </div>
          </div>

          {/* Score */}
          <div className="text-center ml-4">
            <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {idea.score}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{t('ideas.score')}</div>
          </div>
        </div>

        {/* Description with highlights */}
        <p className="text-gray-700 dark:text-gray-300 mb-4 line-clamp-3 [&>span>mark]:bg-yellow-200 dark:[&>span>mark]:bg-yellow-500/30 [&>span>mark]:px-0.5 [&>span>mark]:rounded">
          {renderHighlight(highlights?.description, idea.description || '')}
        </p>

        {/* Tags */}
        {idea.tags && idea.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {idea.tags.slice(0, 5).map((tag) => (
              <TagBadge key={tag.id} tag={tag.display_name} clickable={false} size="sm" />
            ))}
            {idea.tags.length > 5 && (
              <span className="text-xs text-gray-500 dark:text-gray-400 self-center">
                +{idea.tags.length - 5}
              </span>
            )}
          </div>
        )}

        {/* Meta Info */}
        <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
          <div className="flex flex-col gap-1">
            <span>
              {t('ideas.postedBy')}:{' '}
              <span className="font-medium text-gray-700 dark:text-gray-200">
                {getDisplayName(idea.author_display_name)}
              </span>
            </span>
            <span className="text-xs">
              {formatDate(idea.created_at, {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1">
              <span className="text-green-600 dark:text-green-400">+{idea.upvotes}</span>
              <span className="text-gray-400 dark:text-gray-500">/</span>
              <span className="text-red-600 dark:text-red-400">-{idea.downvotes}</span>
            </span>
            <span>
              {idea.comment_count} {t('ideas.comments')}
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}

export default SearchResultItem;
