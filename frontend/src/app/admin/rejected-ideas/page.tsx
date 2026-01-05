'use client';

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { adminAPI } from '@/lib/api';
import type { RejectedIdeaSummary } from '@/types';
import { useToast } from '@/hooks/useToast';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { RefreshCw, XCircle } from 'lucide-react';

export default function RejectedIdeasPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { error: toastError } = useToast();
  const { formatDate, getCategoryName } = useLocalizedField();

  const [ideas, setIdeas] = useState<RejectedIdeaSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(0);

  const limit = 20;

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
      return;
    }
  }, [user, router]);

  useEffect(() => {
    if (user?.is_global_admin) {
      fetchRejectedIdeas();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, user]);

  const fetchRejectedIdeas = async () => {
    setIsLoading(true);
    try {
      const response = await adminAPI.ideas.getRejected({
        skip: page * limit,
        limit,
      });
      setIdeas(response.items);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch rejected ideas:', err);
      toastError('toast.error');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDateTime = (dateString: string) => {
    return formatDate(dateString, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (!user?.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <div className="flex justify-between items-center mb-6">
        <PageHeader title={t('ideaRejection.rejectedIdeas')} />
        <Button variant="secondary" size="sm" onClick={fetchRejectedIdeas} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-primary-500"></div>
          <p className="mt-4 text-gray-500">{t('common.loading')}</p>
        </div>
      ) : ideas.length === 0 ? (
        <Card>
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-gray-100 dark:bg-gray-700 mb-6">
              <XCircle className="w-10 h-10 text-gray-400" />
            </div>
            <p className="text-gray-600 dark:text-gray-300 font-medium">
              {t('ideaRejection.noRejectedIdeas')}
            </p>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {ideas.map((idea) => (
            <Card key={idea.id}>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg text-gray-900 dark:text-gray-100">
                    {idea.title}
                  </h3>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-gray-600 dark:text-gray-400">
                    <span>
                      {t('ideaRejection.author')}: {idea.author_name}
                    </span>
                    <span>
                      {t('ideaRejection.category')}: {getCategoryName(idea)}
                    </span>
                    <span>
                      {t('ideaRejection.createdAt')}: {formatDateTime(idea.created_at)}
                    </span>
                  </div>
                  {idea.admin_comment && (
                    <p className="mt-2 text-sm text-gray-700 dark:text-gray-300">
                      <span className="font-medium">{t('ideaRejection.rejectionReason')}:</span>{' '}
                      {idea.admin_comment}
                    </p>
                  )}
                </div>
              </div>
            </Card>
          ))}

          {/* Pagination */}
          {total > limit && (
            <div className="flex justify-center items-center gap-4 mt-6">
              <Button
                variant="secondary"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                {t('common.previous')}
              </Button>
              <span className="py-2 px-4 text-sm text-gray-600 dark:text-gray-400">
                {page + 1} / {Math.ceil(total / limit)}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={(page + 1) * limit >= total}
                onClick={() => setPage((p) => p + 1)}
              >
                {t('common.next')}
              </Button>
            </div>
          )}
        </div>
      )}
    </PageContainer>
  );
}
