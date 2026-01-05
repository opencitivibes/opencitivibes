'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { Flag, Check, X, Loader2, RefreshCw, Filter, ExternalLink } from 'lucide-react';
import { RichTextDisplay } from '@/components/RichTextDisplay';
import { useAuthStore } from '@/store/authStore';
import { adminModerationAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { Select } from '@/components/Select';
import { Textarea } from '@/components/Textarea';
import { PageContainer } from '@/components/PageContainer';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { formatDistanceToNow } from 'date-fns';
import type { ModerationQueueItem, ContentType, FlagReason, PenaltyType } from '@/types/moderation';
import { FLAG_REASON_LABELS, PENALTY_TYPE_LABELS, getLocalizedLabel } from '@/types/moderation';

export default function ModerationQueuePage() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();

  const [items, setItems] = useState<ModerationQueueItem[]>([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<{ contentType?: ContentType; reason?: FlagReason }>({});
  const [selectedItem, setSelectedItem] = useState<ModerationQueueItem | null>(null);
  const [reviewAction, setReviewAction] = useState<'dismiss' | 'action'>('dismiss');
  const [reviewNotes, setReviewNotes] = useState('');
  const [issuePenalty, setIssuePenalty] = useState(false);
  const [penaltyType, setPenaltyType] = useState<PenaltyType>('warning');
  const [penaltyReason, setPenaltyReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadQueue = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await adminModerationAPI.getQueue(filter.contentType, filter.reason);
      setItems(data.items);
      setPendingCount(data.pending_count);
    } catch (err) {
      console.error('Failed to load moderation queue:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsLoading(false);
    }
  }, [filter, t, toastError]);

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
      return;
    }
    loadQueue();
  }, [user, router, loadQueue]);

  const resetReviewForm = () => {
    setReviewAction('dismiss');
    setReviewNotes('');
    setIssuePenalty(false);
    setPenaltyType('warning');
    setPenaltyReason('');
  };

  const handleReview = async () => {
    if (!selectedItem) return;

    setIsSubmitting(true);
    try {
      const flagIds = selectedItem.flags.map((f) => f.id);
      await adminModerationAPI.reviewFlags(
        flagIds,
        reviewAction,
        reviewNotes || undefined,
        reviewAction === 'action' && issuePenalty,
        reviewAction === 'action' && issuePenalty ? penaltyType : undefined,
        reviewAction === 'action' && issuePenalty ? penaltyReason : undefined
      );

      // Remove from list and close dialog
      setItems((prev) =>
        prev.filter(
          (item) =>
            !(
              item.content_type === selectedItem.content_type &&
              item.content_id === selectedItem.content_id
            )
        )
      );
      setPendingCount((prev) => Math.max(0, prev - selectedItem.flag_count));
      setSelectedItem(null);
      resetReviewForm();
      success(
        reviewAction === 'dismiss'
          ? t('adminModeration.flagsDismissed')
          : t('adminModeration.contentDeleted'),
        { isRaw: true }
      );
    } catch (err) {
      console.error('Failed to review flags:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getReasonLabel = (reason: FlagReason) => {
    return getLocalizedLabel(FLAG_REASON_LABELS[reason], i18n.language);
  };

  const getPenaltyLabel = (penalty: PenaltyType) => {
    return getLocalizedLabel(PENALTY_TYPE_LABELS[penalty], i18n.language);
  };

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">
            {t('adminModeration.queue.title')}
          </h1>
          <Badge variant={pendingCount > 0 ? 'warning' : 'success'} size="md">
            {pendingCount} {t('adminModeration.pending')}
          </Badge>
        </div>
        <Button variant="secondary" size="sm" onClick={loadQueue} disabled={isLoading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          {t('common.refresh')}
        </Button>
      </div>

      {/* Filters */}
      <Card className="mb-6 bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center gap-2 mb-3">
            <Filter className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('adminModeration.filter.title')}:
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-md">
            <Select
              label={t('adminModeration.filter.contentType')}
              value={filter.contentType || ''}
              onChange={(e) =>
                setFilter((prev) => ({
                  ...prev,
                  contentType: e.target.value ? (e.target.value as ContentType) : undefined,
                }))
              }
              fullWidth={true}
              className="text-sm"
            >
              <option value="">{t('adminModeration.filter.all')}</option>
              <option value="comment">{t('moderation.comment')}</option>
              <option value="idea">{t('moderation.idea')}</option>
            </Select>

            <Select
              label={t('adminModeration.filter.reason')}
              value={filter.reason || ''}
              onChange={(e) =>
                setFilter((prev) => ({
                  ...prev,
                  reason: e.target.value ? (e.target.value as FlagReason) : undefined,
                }))
              }
              fullWidth={true}
              className="text-sm"
            >
              <option value="">{t('adminModeration.filter.allReasons')}</option>
              {(Object.keys(FLAG_REASON_LABELS) as FlagReason[]).map((key) => (
                <option key={key} value={key}>
                  {getReasonLabel(key)}
                </option>
              ))}
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Queue Items */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : items.length === 0 ? (
        <Card className="bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700">
          <CardContent className="py-12 text-center">
            <Check className="h-12 w-12 mx-auto text-success-500 mb-4" />
            <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {t('adminModeration.queue.empty')}
            </p>
            <p className="text-gray-500 dark:text-gray-400">
              {t('adminModeration.queue.emptyDescription')}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {items.map((item) => (
            <Card
              key={`${item.content_type}-${item.content_id}`}
              className={`bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 ${item.is_hidden ? 'border-warning-300 dark:border-warning-600 bg-warning-50/50 dark:bg-warning-900/20' : ''}`}
            >
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <Badge
                        variant={item.content_type === 'comment' ? 'secondary' : 'primary'}
                        size="sm"
                      >
                        {item.content_type === 'comment'
                          ? t('moderation.comment')
                          : t('moderation.idea')}
                      </Badge>
                      <span className="text-gray-600 dark:text-gray-400 text-sm">
                        {t('ideas.postedBy')}: @{item.content_author_username}
                      </span>
                    </CardTitle>
                    <CardDescription className="mt-1 text-gray-500 dark:text-gray-400">
                      {formatDistanceToNow(new Date(item.content_created_at), {
                        addSuffix: true,
                      })}
                      {' | '}
                      {t('adminModeration.trustScore')}: {item.author_trust_score}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="error" size="sm">
                      <Flag className="h-3 w-3 mr-1" />
                      {item.flag_count}
                    </Badge>
                    {item.is_hidden && (
                      <Badge variant="warning" size="sm">
                        {t('adminModeration.hidden')}
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-3 mb-4">
                  <RichTextDisplay
                    content={item.content_text}
                    className="text-sm text-gray-900 dark:text-gray-100"
                  />
                </div>

                {item.content_type === 'comment' && item.idea_id && (
                  <div className="mb-4">
                    <a
                      href={`/ideas/${item.idea_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-primary-500 dark:text-primary-400 hover:text-primary-600 dark:hover:text-primary-300 hover:underline"
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      {t('adminModeration.viewContext')}
                    </a>
                  </div>
                )}

                <div className="flex flex-wrap gap-2 mb-4">
                  {item.flags.map((flag) => (
                    <Badge key={flag.id} variant="secondary" size="sm">
                      {getReasonLabel(flag.reason)}
                      {flag.details && ` - "${flag.details.slice(0, 30)}..."`}
                    </Badge>
                  ))}
                </div>

                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setSelectedItem(item);
                      setReviewAction('dismiss');
                    }}
                  >
                    <Check className="h-4 w-4 mr-1" />
                    {t('adminModeration.dismiss')}
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    className="bg-error-600 hover:bg-error-700 border-error-600"
                    onClick={() => {
                      setSelectedItem(item);
                      setReviewAction('action');
                    }}
                  >
                    <X className="h-4 w-4 mr-1" />
                    {t('adminModeration.delete')}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Review Dialog */}
      <Dialog open={!!selectedItem} onOpenChange={() => setSelectedItem(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {reviewAction === 'dismiss'
                ? t('adminModeration.dialog.dismissTitle')
                : t('adminModeration.dialog.actionTitle')}
            </DialogTitle>
            <DialogDescription>
              {reviewAction === 'dismiss'
                ? t('adminModeration.dialog.dismissDescription')
                : t('adminModeration.dialog.actionDescription')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Textarea
              label={t('adminModeration.dialog.notes')}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder={t('adminModeration.dialog.notesPlaceholder')}
              rows={3}
            />

            {reviewAction === 'action' && (
              <div className="space-y-4 border-t pt-4">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="issue-penalty"
                    checked={issuePenalty}
                    onCheckedChange={(checked) => setIssuePenalty(!!checked)}
                  />
                  <Label htmlFor="issue-penalty" className="text-sm font-medium cursor-pointer">
                    {t('adminModeration.dialog.issuePenalty')}
                  </Label>
                </div>

                {issuePenalty && (
                  <>
                    <Select
                      label={t('adminModeration.dialog.penaltyType')}
                      value={penaltyType}
                      onChange={(e) => setPenaltyType(e.target.value as PenaltyType)}
                    >
                      {(Object.keys(PENALTY_TYPE_LABELS) as PenaltyType[]).map((key) => (
                        <option key={key} value={key}>
                          {getPenaltyLabel(key)}
                        </option>
                      ))}
                    </Select>

                    <Textarea
                      label={t('adminModeration.dialog.penaltyReason')}
                      value={penaltyReason}
                      onChange={(e) => setPenaltyReason(e.target.value)}
                      placeholder={t('adminModeration.dialog.penaltyReasonPlaceholder')}
                      rows={2}
                    />
                  </>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => setSelectedItem(null)}
              disabled={isSubmitting}
            >
              {t('common.cancel')}
            </Button>
            <Button
              variant="primary"
              className={
                reviewAction === 'dismiss' ? '' : 'bg-error-600 hover:bg-error-700 border-error-600'
              }
              onClick={handleReview}
              disabled={isSubmitting || (issuePenalty && !penaltyReason)}
              loading={isSubmitting}
            >
              {reviewAction === 'dismiss'
                ? t('adminModeration.dialog.dismissConfirm')
                : t('adminModeration.dialog.deleteConfirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
