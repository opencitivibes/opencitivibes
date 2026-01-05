'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { Scale, Check, X, Loader2, RefreshCw, Clock } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { adminModerationAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { Textarea } from '@/components/Textarea';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { formatDistanceToNow } from 'date-fns';
import type { AppealResponse } from '@/types/moderation';

export default function AppealsQueuePage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();

  const [appeals, setAppeals] = useState<AppealResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedAppeal, setSelectedAppeal] = useState<AppealResponse | null>(null);
  const [reviewAction, setReviewAction] = useState<'approve' | 'reject'>('approve');
  const [reviewNotes, setReviewNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadAppeals = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await adminModerationAPI.getPendingAppeals();
      setAppeals(data.appeals);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to load appeals:', err);
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
    loadAppeals();
  }, [user, router, loadAppeals]);

  const handleReviewAppeal = async () => {
    if (!selectedAppeal || !reviewNotes.trim()) return;

    setIsSubmitting(true);
    try {
      await adminModerationAPI.reviewAppeal(selectedAppeal.id, reviewAction, reviewNotes);
      success(
        reviewAction === 'approve'
          ? t('adminModeration.appealApproved')
          : t('adminModeration.appealRejected'),
        { isRaw: true }
      );
      setSelectedAppeal(null);
      setReviewNotes('');
      loadAppeals();
    } catch (err) {
      console.error('Failed to review appeal:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <div className="mb-6 space-y-4">
        <PageHeader title={t('adminModeration.appeals.title')} />
        <div className="flex items-center gap-4">
          <Badge variant={total > 0 ? 'warning' : 'success'} size="lg">
            {total} {t('adminModeration.appeals.pending')}
          </Badge>
          <Button variant="secondary" onClick={loadAppeals} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : appeals.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Scale className="h-12 w-12 mx-auto text-success-500 mb-4" />
            <p className="text-lg font-medium text-gray-900">
              {t('adminModeration.appeals.empty')}
            </p>
            <p className="text-gray-500">{t('adminModeration.appeals.emptyDescription')}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {appeals.map((appeal) => (
            <Card key={appeal.id}>
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Scale className="h-4 w-4" />
                      {t('adminModeration.appeals.appealFor')} #{appeal.penalty_id}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      <Clock className="h-3 w-3 inline mr-1" />
                      {t('adminModeration.appeals.submittedAt')}{' '}
                      {formatDistanceToNow(new Date(appeal.created_at), { addSuffix: true })}
                    </CardDescription>
                  </div>
                  <Badge variant="warning">{t('adminModeration.appeals.pendingReview')}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-3 mb-4">
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-1">
                    {t('adminModeration.appeals.userReason')}:
                  </p>
                  <p className="text-sm text-amber-900 dark:text-amber-100 whitespace-pre-wrap">
                    {appeal.reason}
                  </p>
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    className="bg-success-600 hover:bg-success-700 border-success-600"
                    onClick={() => {
                      setSelectedAppeal(appeal);
                      setReviewAction('approve');
                    }}
                  >
                    <Check className="h-4 w-4 mr-1" />
                    {t('adminModeration.appeals.approve')}
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    className="bg-error-600 hover:bg-error-700 border-error-600"
                    onClick={() => {
                      setSelectedAppeal(appeal);
                      setReviewAction('reject');
                    }}
                  >
                    <X className="h-4 w-4 mr-1" />
                    {t('adminModeration.appeals.reject')}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Review Appeal Dialog */}
      <Dialog open={!!selectedAppeal} onOpenChange={() => setSelectedAppeal(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              {reviewAction === 'approve'
                ? t('adminModeration.appeals.approveTitle')
                : t('adminModeration.appeals.rejectTitle')}
            </DialogTitle>
            <DialogDescription>
              {reviewAction === 'approve'
                ? t('adminModeration.appeals.approveDescription')
                : t('adminModeration.appeals.rejectDescription')}
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <Textarea
              label={t('adminModeration.appeals.reviewNotes')}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder={t('adminModeration.appeals.reviewNotesPlaceholder')}
              rows={3}
            />
          </div>

          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => setSelectedAppeal(null)}
              disabled={isSubmitting}
            >
              {t('common.cancel')}
            </Button>
            <Button
              variant="primary"
              className={
                reviewAction === 'approve'
                  ? 'bg-success-600 hover:bg-success-700 border-success-600'
                  : 'bg-error-600 hover:bg-error-700 border-error-600'
              }
              onClick={handleReviewAppeal}
              disabled={isSubmitting || !reviewNotes.trim()}
              loading={isSubmitting}
            >
              {reviewAction === 'approve'
                ? t('adminModeration.appeals.confirmApprove')
                : t('adminModeration.appeals.confirmReject')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
