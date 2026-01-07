'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { adminAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { RichTextDisplay } from '@/components/RichTextDisplay';
import { Textarea } from '@/components/Textarea';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { DataFreshness } from '@/components/DataFreshness';
import { ModerationListSkeleton } from '@/components/admin/AnalyticsSkeleton';
import { Edit2 } from 'lucide-react';
import type { Idea } from '@/types';

export default function AdminPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();
  const { getCategoryName, getDisplayName } = useLocalizedField();

  // Pagination state
  const [pendingIdeas, setPendingIdeas] = useState<Idea[]>([]);
  const [totalPending, setTotalPending] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Moderation state
  const [selectedIdea, setSelectedIdea] = useState<Idea | null>(null);
  const [adminComment, setAdminComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadPendingIdeas = useCallback(
    async (reset: boolean = false) => {
      try {
        if (reset) {
          setIsLoading(true);
        } else {
          setIsLoadingMore(true);
        }
        setLoadError(null);

        const skip = reset ? 0 : pendingIdeas.length;
        const data = await adminAPI.getPendingIdeas(skip, 20);

        if (reset) {
          setPendingIdeas(data.items);
        } else {
          setPendingIdeas((prev) => [...prev, ...data.items]);
        }

        setTotalPending(data.total);
        setHasMore(data.has_more);
        setLastUpdated(new Date());
      } catch (err) {
        console.error('Error loading pending ideas:', err);
        setLoadError(t('admin.loadError'));
      } finally {
        setIsLoading(false);
        setIsLoadingMore(false);
      }
    },
    [pendingIdeas.length, t]
  );

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
      return;
    }

    loadPendingIdeas(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, router]);

  const handleModerate = async (ideaId: number, status: 'approved' | 'rejected') => {
    setIsSubmitting(true);
    try {
      await adminAPI.moderateIdea(ideaId, status, adminComment || undefined);
      success(status === 'approved' ? 'toast.ideaApproved' : 'toast.ideaRejected');
      setSelectedIdea(null);
      setAdminComment('');
      // Refresh the list after moderation
      await loadPendingIdeas(true);
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error moderating idea:', err);
      toastError(axiosError.response?.data?.detail || t('toast.error'), { isRaw: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!user || !user.is_global_admin) {
    return null;
  }

  const remainingCount = totalPending - pendingIdeas.length;

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <PageHeader title={t('admin.title')} />

      {/* Pending Ideas Section */}
      <Card>
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-3">
            {t('admin.pendingIdeas')}
          </h2>
          <div className="flex items-center justify-between">
            <DataFreshness
              lastUpdated={lastUpdated}
              onRefresh={() => loadPendingIdeas(true)}
              isRefreshing={isLoading}
            />
            <Badge variant={totalPending > 0 ? 'warning' : 'success'} size="md">
              {totalPending} {t('admin.pending')}
            </Badge>
          </div>
        </div>

        {/* Loading state */}
        {isLoading && pendingIdeas.length === 0 && <ModerationListSkeleton count={3} />}

        {/* Error state */}
        {loadError && !isLoading && (
          <div className="text-center py-8">
            <p className="text-error-600 dark:text-error-400 mb-4">{loadError}</p>
            <Button onClick={() => loadPendingIdeas(true)} variant="secondary">
              {t('common.retry')}
            </Button>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !loadError && pendingIdeas.length === 0 && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-success-50 dark:bg-success-900/20 mb-6">
              <svg
                className="w-10 h-10 text-success-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              {t('admin.noPendingIdeas')}
            </h3>
            <p className="text-gray-600 dark:text-gray-400">{t('admin.allCaughtUp')}</p>
          </div>
        )}

        {/* Ideas list */}
        {!isLoading && !loadError && pendingIdeas.length > 0 && (
          <div className="space-y-4">
            {pendingIdeas.map((idea) => (
              <div
                key={idea.id}
                className="border border-gray-200 dark:border-gray-700 rounded-xl p-6 hover:shadow-lg hover:border-primary-200 dark:hover:border-primary-600 transition bg-white dark:bg-gray-800"
              >
                {/* Idea Info */}
                <div className="mb-4">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-3">
                    {idea.title}
                  </h3>
                  <div className="flex flex-wrap gap-2 mb-3">
                    <Badge variant="primary">{getCategoryName(idea)}</Badge>
                    {/* Show "Edited" badge for pending_edit status */}
                    {idea.status === 'pending_edit' && (
                      <Badge variant="pending_edit">
                        <Edit2 className="h-3 w-3 mr-1" />
                        {t('admin.editedIdea', 'Edited Idea')}
                      </Badge>
                    )}
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {t('ideas.postedBy')}:{' '}
                      <span className="font-medium">
                        {getDisplayName(idea.author_display_name)}
                      </span>
                    </span>
                    {/* Show edit count for pending_edit */}
                    {idea.status === 'pending_edit' && idea.edit_count && (
                      <span className="text-sm text-purple-600 dark:text-purple-400">
                        {t('admin.editCount', 'Edit count: {{count}}', { count: idea.edit_count })}
                      </span>
                    )}
                  </div>
                  <RichTextDisplay content={idea.description} />
                </div>

                {/* Moderation Controls */}
                {selectedIdea?.id === idea.id ? (
                  <div className="border-t border-gray-200 dark:border-gray-700 pt-4 space-y-4">
                    <Textarea
                      label={t('admin.adminComment')}
                      value={adminComment}
                      onChange={(e) => setAdminComment(e.target.value)}
                      rows={3}
                      placeholder="Optional comment for rejection..."
                      disabled={isSubmitting}
                    />

                    <div className="flex flex-wrap gap-3">
                      <Button
                        onClick={() => handleModerate(idea.id, 'approved')}
                        disabled={isSubmitting}
                        loading={isSubmitting}
                        variant="primary"
                        className="bg-success-600 hover:bg-success-700 border-success-600"
                      >
                        <span className="mr-2">+</span> {t('admin.approve')}
                      </Button>
                      <Button
                        onClick={() => handleModerate(idea.id, 'rejected')}
                        disabled={isSubmitting}
                        loading={isSubmitting}
                        variant="primary"
                        className="bg-error-600 hover:bg-error-700 border-error-600"
                      >
                        <span className="mr-2">x</span> {t('admin.reject')}
                      </Button>
                      <Button
                        onClick={() => {
                          setSelectedIdea(null);
                          setAdminComment('');
                        }}
                        disabled={isSubmitting}
                        variant="secondary"
                      >
                        {t('common.cancel')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                    <Button onClick={() => setSelectedIdea(idea)} variant="primary">
                      {t('admin.moderate')}
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Load More Button */}
        {hasMore && !isLoading && !loadError && (
          <div className="text-center pt-6">
            <Button
              onClick={() => loadPendingIdeas(false)}
              loading={isLoadingMore}
              variant="secondary"
              size="lg"
            >
              {isLoadingMore ? (
                t('common.loading')
              ) : (
                <>
                  {t('common.loadMore')}
                  <span className="ml-2 text-gray-500">
                    ({remainingCount} {t('common.remaining')})
                  </span>
                </>
              )}
            </Button>
          </div>
        )}

        {/* All loaded indicator */}
        {!hasMore && pendingIdeas.length > 0 && !isLoading && (
          <p className="text-center text-sm text-gray-500 dark:text-gray-400 pt-6">
            {t('admin.allLoaded', { count: totalPending })}
          </p>
        )}
      </Card>
    </PageContainer>
  );
}
