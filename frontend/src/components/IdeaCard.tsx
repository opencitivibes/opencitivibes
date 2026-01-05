'use client';

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { MessageCircle } from 'lucide-react';
import { htmlToPlainText } from '@/lib/sanitize';
import TagBadge from '@/components/TagBadge';
import { FlagButton } from '@/components/moderation';
import { VotingButtons } from '@/components/VotingButtons';
import { QualityBadges } from '@/components/QualityBadges';
import { LanguageBadge } from '@/components/LanguageBadge';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import type { Idea } from '@/types';

interface IdeaCardProps {
  idea: Idea;
  onVoteUpdate?: () => void;
  onClick?: () => void;
  onCategoryClick?: (categoryId: number) => void;
  hideStatus?: boolean;
}

export default function IdeaCard({
  idea,
  onVoteUpdate,
  onClick,
  onCategoryClick,
  hideStatus = false,
}: IdeaCardProps) {
  const { t } = useTranslation();
  const { getField, formatDate, getDisplayName } = useLocalizedField();

  const categoryName = getField(
    { name_fr: idea.category_name_fr, name_en: idea.category_name_en },
    'name'
  );

  // Extract plain text from description for preview (handles rich text content)
  const descriptionPreview = useMemo(() => htmlToPlainText(idea.description), [idea.description]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-100 text-green-800';
      case 'rejected':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <article
      className="relative bg-white dark:bg-gray-800 rounded-xl shadow-md p-6 border border-gray-100 dark:border-gray-700 hover:shadow-xl hover:-translate-y-1 hover:border-primary-200 dark:hover:border-primary-600 transition-all duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
      onClick={onClick}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
      role={onClick ? 'button' : undefined}
    >
      {/* Quality Badges (positioned absolute top-right) */}
      {idea.status === 'approved' && <QualityBadges counts={idea.quality_counts} />}

      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100">{idea.title}</h3>
            <LanguageBadge language={idea.language} size="sm" />
          </div>
          <div className="flex flex-wrap gap-2 text-sm text-gray-600 dark:text-gray-400">
            {onCategoryClick ? (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onCategoryClick(idea.category_id);
                }}
                className="px-2.5 py-1 bg-primary-100 dark:bg-primary-900/50 text-primary-800 dark:text-primary-200 rounded-md font-medium text-sm border border-primary-200/50 dark:border-primary-700/50 hover:bg-primary-200 dark:hover:bg-primary-800/70 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 dark:focus:ring-offset-gray-800"
                aria-label={`Filter by category: ${categoryName}`}
              >
                {categoryName}
              </button>
            ) : (
              <span className="px-2.5 py-1 bg-primary-100 dark:bg-primary-900/50 text-primary-800 dark:text-primary-200 rounded-md font-medium text-sm border border-primary-200/50 dark:border-primary-700/50">
                {categoryName}
              </span>
            )}
            {!hideStatus && (
              <span className={`px-2 py-1 rounded ${getStatusColor(idea.status)}`}>
                {t(`ideas.status.${idea.status}`)}
              </span>
            )}
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

      {/* Description */}
      <p className="text-gray-700 dark:text-gray-300 mb-4 line-clamp-3">{descriptionPreview}</p>

      {/* Tags */}
      {idea.tags && idea.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {idea.tags.map((tag) => (
            <TagBadge key={tag.id} tag={tag.display_name} clickable={true} size="sm" />
          ))}
        </div>
      )}

      {/* Meta Info */}
      <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 mb-4">
        <div className="flex items-center gap-3">
          {/* Author Avatar */}
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-primary-100 dark:bg-primary-900/40 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-medium text-primary-600 dark:text-primary-400">
                {getDisplayName(idea.author_display_name).charAt(0).toUpperCase()}
              </span>
            </div>
            <span className="font-medium text-gray-700 dark:text-gray-300">
              {getDisplayName(idea.author_display_name)}
            </span>
          </div>
          <span className="text-gray-300 dark:text-gray-600">•</span>
          <time dateTime={idea.created_at} className="text-gray-500 dark:text-gray-400">
            {formatDate(idea.created_at, {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </time>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400">
            <MessageCircle className="w-4 h-4" aria-hidden="true" />
            <span>{idea.comment_count}</span>
            <span className="sr-only">{t('ideas.comments')}</span>
          </span>
          <FlagButton
            contentType="idea"
            contentId={idea.id}
            contentAuthorId={idea.user_id}
            contentPreview={`${idea.title}: ${descriptionPreview.slice(0, 200)}`}
          />
        </div>
      </div>

      {/* Voting Buttons */}
      {idea.status === 'approved' && (
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
          <VotingButtons
            ideaId={idea.id}
            upvotes={idea.upvotes}
            downvotes={idea.downvotes}
            score={idea.score}
            userVote={idea.user_vote}
            onVoteUpdate={onVoteUpdate}
            variant="compact"
            showScore={false}
          />
        </div>
      )}

      {/* Admin Comment (if rejected) */}
      {idea.status === 'rejected' && idea.admin_comment && (
        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm font-medium text-red-800 dark:text-red-300">
            {t('ideas.adminComment')}:
          </p>
          <p className="text-sm text-red-700 dark:text-red-400">{idea.admin_comment}</p>
        </div>
      )}
    </article>
  );
}
