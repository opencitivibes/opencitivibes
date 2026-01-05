'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { officialsAPI } from '@/lib/api';
import type { OfficialsIdeaDetail } from '@/types';
import {
  ArrowLeft,
  ThumbsUp,
  ThumbsDown,
  Calendar,
  User,
  Tag,
  BarChart3,
  Heart,
  Sun,
  AlertTriangle,
  Handshake,
  Leaf,
  Users,
  TreeDeciduous,
  Baby,
  MessageSquare,
} from 'lucide-react';
import Link from 'next/link';

// Render icon based on icon name from API
function QualityIcon({ iconName, className }: { iconName: string | null; className?: string }) {
  switch (iconName) {
    case 'heart':
      return <Heart className={className} />;
    case 'sun':
      return <Sun className={className} />;
    case 'alert-triangle':
      return <AlertTriangle className={className} />;
    case 'hand-helping':
      return <Handshake className={className} />;
    case 'leaf':
      return <Leaf className={className} />;
    case 'users':
      return <Users className={className} />;
    case 'tree':
      return <TreeDeciduous className={className} />;
    case 'baby':
      return <Baby className={className} />;
    default:
      return <Heart className={className} />;
  }
}

export default function OfficialsIdeaDetailPage() {
  const { t } = useTranslation();
  const { getCategoryName, getQualityName, getDisplayName } = useLocalizedField();
  const params = useParams();
  const router = useRouter();
  const [idea, setIdea] = useState<OfficialsIdeaDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const ideaId = Number(params.id);

  useEffect(() => {
    if (!ideaId || isNaN(ideaId)) {
      setError('Invalid idea ID');
      setIsLoading(false);
      return;
    }

    const fetchIdea = async () => {
      setIsLoading(true);
      try {
        const data = await officialsAPI.getIdeaDetail(ideaId);
        setIdea(data);
      } catch (err) {
        console.error('Failed to fetch idea:', err);
        setError('Failed to load idea details');
      } finally {
        setIsLoading(false);
      }
    };

    fetchIdea();
  }, [ideaId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error || !idea) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">{error || 'Idea not found'}</p>
        <button
          onClick={() => router.push('/officials/ideas')}
          className="mt-4 text-primary-600 hover:underline"
        >
          {t('common.back')}
        </button>
      </div>
    );
  }

  const categoryName = getCategoryName(idea);

  return (
    <div className="space-y-6">
      {/* Header with back button */}
      <div className="flex items-center gap-4">
        <Link
          href="/officials/ideas"
          className="flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>{t('officials.backToIdeas')}</span>
        </Link>
      </div>

      {/* Idea card */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        {/* Title and status */}
        <div className="flex items-start justify-between gap-4 mb-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{idea.title}</h1>
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              idea.status === 'approved'
                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                : idea.status === 'rejected'
                  ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                  : 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
            }`}
          >
            {t(`ideas.status.${idea.status}`)}
          </span>
        </div>

        {/* Meta info */}
        <div className="flex flex-wrap gap-4 mb-6 text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center gap-1">
            <User className="w-4 h-4" />
            <span>{getDisplayName(idea.author_display_name)}</span>
          </div>
          <div className="flex items-center gap-1">
            <Tag className="w-4 h-4" />
            <span>{categoryName}</span>
          </div>
          <div className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            <span>{new Date(idea.created_at).toLocaleDateString()}</span>
          </div>
        </div>

        {/* Description */}
        <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap mb-6">
          {idea.description}
        </p>

        {/* Vote stats */}
        <div className="flex items-center gap-6 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg mb-6">
          <div className="flex items-center gap-2">
            <ThumbsUp className="w-5 h-5 text-green-600" />
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {idea.upvotes}
            </span>
            <span className="text-sm text-gray-500">{t('officials.upvotes')}</span>
          </div>
          <div className="flex items-center gap-2">
            <ThumbsDown className="w-5 h-5 text-red-600" />
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {idea.downvotes}
            </span>
            <span className="text-sm text-gray-500">{t('officials.downvotes')}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-primary-600">
              {idea.score > 0 ? '+' : ''}
              {idea.score}
            </span>
            <span className="text-sm text-gray-500">{t('officials.score')}</span>
          </div>
        </div>
      </div>

      {/* Quality breakdown */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('officials.qualityBreakdown')}
          </h2>
          <span className="text-sm text-gray-500">
            ({idea.quality_count} {t('officials.total')})
          </span>
        </div>

        {idea.quality_breakdown.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-400 italic">{t('officials.noQualitiesYet')}</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {idea.quality_breakdown.map((quality) => {
              const qualityName = getQualityName(quality);
              const percentage =
                idea.quality_count > 0 ? Math.round((quality.count / idea.quality_count) * 100) : 0;

              return (
                <div
                  key={quality.quality_key}
                  className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                >
                  <QualityIcon
                    iconName={quality.icon}
                    className="w-6 h-6 text-gray-600 dark:text-gray-400"
                  />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium text-gray-900 dark:text-white">
                        {qualityName}
                      </span>
                      <span className="text-sm font-semibold text-primary-600">
                        {quality.count}
                      </span>
                    </div>
                    <div className="h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${percentage}%`,
                          backgroundColor: quality.color || '#3b82f6',
                        }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Top Liked Comments */}
      {idea.top_comments && idea.top_comments.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {t('officials.topComments')}
            </h2>
            <span className="text-sm text-gray-500">({idea.top_comments.length})</span>
          </div>

          <div className="space-y-4">
            {idea.top_comments.map((comment) => (
              <div key={comment.id} className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-medium text-gray-900 dark:text-white">
                        {getDisplayName(comment.author_display_name)}
                      </span>
                      <span className="text-xs text-gray-500">
                        {new Date(comment.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-gray-700 dark:text-gray-300 text-sm whitespace-pre-wrap">
                      {comment.content}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 px-2 py-1 bg-rose-100 dark:bg-rose-900/30 rounded-full shrink-0">
                    <Heart className="w-4 h-4 text-rose-600 dark:text-rose-400" />
                    <span className="text-sm font-medium text-rose-600 dark:text-rose-400">
                      {comment.like_count}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Link to public idea page */}
      <div className="text-center">
        <Link href={`/ideas/${idea.id}`} className="text-primary-600 hover:underline text-sm">
          {t('officials.viewPublicPage')}
        </Link>
      </div>
    </div>
  );
}
