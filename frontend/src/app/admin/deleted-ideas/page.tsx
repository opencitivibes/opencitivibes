'use client';

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { adminAPI } from '@/lib/api';
import type { DeletedIdeaSummary } from '@/types';
import { useToast } from '@/hooks/useToast';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Badge } from '@/components/Badge';
import { RefreshCw, Undo2 } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

export default function DeletedIdeasPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();
  const { formatDate } = useLocalizedField();

  const [ideas, setIdeas] = useState<DeletedIdeaSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [restoringId, setRestoringId] = useState<number | null>(null);

  const limit = 20;

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
      return;
    }
  }, [user, router]);

  useEffect(() => {
    if (user?.is_global_admin) {
      fetchDeletedIdeas();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, user]);

  const fetchDeletedIdeas = async () => {
    setIsLoading(true);
    try {
      const response = await adminAPI.ideas.getDeleted({
        skip: page * limit,
        limit,
      });
      setIdeas(response.items);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch deleted ideas:', err);
      toastError('toast.error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRestore = async (ideaId: number) => {
    setRestoringId(ideaId);
    try {
      await adminAPI.ideas.restore(ideaId);
      success('toast.ideaRestored');
      // Refresh list
      fetchDeletedIdeas();
    } catch (err) {
      console.error('Failed to restore idea:', err);
      toastError('toast.error');
    } finally {
      setRestoringId(null);
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
        <PageHeader title={t('ideaDeletion.deletedIdeas')} />
        <Button variant="secondary" size="sm" onClick={fetchDeletedIdeas} disabled={isLoading}>
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
              <svg
                className="w-10 h-10 text-gray-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </div>
            <p className="text-gray-600 dark:text-gray-300 font-medium">
              {t('ideaDeletion.noDeletedIdeas')}
            </p>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          {ideas.map((idea) => (
            <Card key={idea.id}>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="font-semibold text-lg text-gray-900">{idea.title}</h3>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm text-gray-600">
                    <span>
                      {t('ideaDeletion.originalAuthor')}: {idea.original_author_name}
                    </span>
                    <span>
                      {t('ideaDeletion.deletedAt')}: {formatDateTime(idea.deleted_at)}
                    </span>
                    {idea.deleted_by_name && (
                      <span>
                        {t('ideaDeletion.deletedBy')}: {idea.deleted_by_name}
                      </span>
                    )}
                  </div>
                  {idea.deletion_reason && (
                    <p className="mt-2 text-sm">
                      <span className="font-medium">{t('ideaDeletion.reason')}:</span>{' '}
                      {idea.deletion_reason}
                    </p>
                  )}
                  <div className="mt-3">
                    <Badge variant={idea.status as 'pending' | 'approved' | 'rejected'}>
                      {t(`ideas.status.${idea.status}`)}
                    </Badge>
                  </div>
                </div>
                <div className="ml-4">
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="secondary" size="sm" disabled={restoringId === idea.id}>
                        <Undo2 className="h-4 w-4 mr-2" />
                        {t('ideaDeletion.restore')}
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent className="bg-white">
                      <AlertDialogHeader>
                        <AlertDialogTitle>{t('ideaDeletion.restoreConfirm')}</AlertDialogTitle>
                        <AlertDialogDescription>&quot;{idea.title}&quot;</AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>{t('ideaDeletion.cancelButton')}</AlertDialogCancel>
                        <AlertDialogAction onClick={() => handleRestore(idea.id)}>
                          {t('ideaDeletion.restore')}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
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
              <span className="py-2 px-4 text-sm text-gray-600">
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
