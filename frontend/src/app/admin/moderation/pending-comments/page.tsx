'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { MessageSquare, Check, X, Loader2, RefreshCw, Clock, ExternalLink } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { adminModerationAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { formatDistanceToNow } from 'date-fns';
import Link from 'next/link';
import { RichTextDisplay } from '@/components/RichTextDisplay';
import type { PendingComment } from '@/types/moderation';

export default function PendingCommentsPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();

  const [comments, setComments] = useState<PendingComment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());

  const loadComments = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await adminModerationAPI.getPendingComments();
      setComments(data);
    } catch (err) {
      console.error('Failed to load pending comments:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsLoading(false);
    }
  }, [t, toastError]);

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
      return;
    }
    loadComments();
  }, [user, router, loadComments]);

  const handleApprove = async (commentId: number) => {
    setProcessingIds((prev) => new Set(prev).add(commentId));
    try {
      await adminModerationAPI.approveComment(commentId);
      success(t('adminModeration.comments.approved'), { isRaw: true });
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch (err) {
      console.error('Failed to approve comment:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(commentId);
        return next;
      });
    }
  };

  const handleReject = async (commentId: number) => {
    if (!confirm(t('adminModeration.comments.rejectConfirm'))) return;

    setProcessingIds((prev) => new Set(prev).add(commentId));
    try {
      await adminModerationAPI.rejectComment(commentId);
      success(t('adminModeration.comments.rejected'), { isRaw: true });
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch (err) {
      console.error('Failed to reject comment:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(commentId);
        return next;
      });
    }
  };

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6">
        <PageHeader title={t('adminModeration.comments.title')} />
        <div className="flex items-center gap-2 sm:gap-4">
          <Badge
            variant={comments.length > 0 ? 'warning' : 'success'}
            size="sm"
            className="sm:text-sm"
          >
            {comments.length} {t('adminModeration.comments.pending')}
          </Badge>
          <Button variant="secondary" size="sm" onClick={loadComments} disabled={isLoading}>
            <RefreshCw
              className={`h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1.5 sm:mr-2 ${isLoading ? 'animate-spin' : ''}`}
            />
            <span className="hidden sm:inline">{t('common.refresh')}</span>
            <span className="sm:hidden">{t('common.refresh')}</span>
          </Button>
        </div>
      </div>

      <p className="text-gray-500 dark:text-gray-400 mb-6 text-sm sm:text-base">
        {t('adminModeration.comments.description')}
      </p>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : comments.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <MessageSquare className="h-12 w-12 mx-auto text-success-500 mb-4" />
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {t('adminModeration.comments.empty')}
            </p>
            <p className="text-gray-500 dark:text-gray-400">
              {t('adminModeration.comments.emptyDescription')}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {comments.map((comment) => (
            <Card key={comment.id}>
              <CardHeader className="pb-2 px-3 sm:px-6">
                <div className="flex flex-col sm:flex-row justify-between items-start gap-2">
                  <div className="min-w-0 flex-1">
                    <CardTitle className="flex items-center gap-1.5 sm:gap-2 text-sm sm:text-base">
                      <MessageSquare className="h-3.5 w-3.5 sm:h-4 sm:w-4 flex-shrink-0" />
                      <span className="truncate">
                        {t('adminModeration.comments.by')} @{comment.author_username}
                      </span>
                    </CardTitle>
                    <CardDescription className="mt-1 flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
                      <Clock className="h-3 w-3 flex-shrink-0" />
                      <span>
                        {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
                      </span>
                      <span className="text-gray-400 dark:text-gray-500">|</span>
                      <Link
                        href={`/ideas/${comment.idea_id}`}
                        className="text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
                      >
                        {t('adminModeration.comments.viewIdea')}
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </CardDescription>
                  </div>
                  <Badge variant="warning" size="sm" className="flex-shrink-0">
                    {t('adminModeration.comments.awaitingApproval')}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="px-3 sm:px-6">
                <div className="bg-gray-100 dark:bg-gray-700/50 rounded-lg p-2.5 sm:p-3 mb-3 sm:mb-4">
                  <RichTextDisplay
                    content={comment.content}
                    className="text-sm text-gray-800 dark:text-gray-200"
                  />
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    className="bg-success-600 hover:bg-success-700 border-success-600 text-xs sm:text-sm"
                    onClick={() => handleApprove(comment.id)}
                    disabled={processingIds.has(comment.id)}
                    loading={processingIds.has(comment.id)}
                  >
                    <Check className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1" />
                    {t('admin.approve')}
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    className="bg-error-600 hover:bg-error-700 border-error-600 text-xs sm:text-sm"
                    onClick={() => handleReject(comment.id)}
                    disabled={processingIds.has(comment.id)}
                  >
                    <X className="h-3.5 w-3.5 sm:h-4 sm:w-4 mr-1" />
                    {t('admin.reject')}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </PageContainer>
  );
}
