'use client';

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { RichTextDisplay } from '@/components/RichTextDisplay';

interface RejectCommentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  commentContent: string;
  authorUsername: string;
  onConfirm: (reason?: string) => Promise<void>;
  isLoading?: boolean;
}

export function RejectCommentDialog({
  open,
  onOpenChange,
  commentContent,
  authorUsername,
  onConfirm,
  isLoading = false,
}: RejectCommentDialogProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConfirm = async () => {
    setIsSubmitting(true);
    try {
      await onConfirm(reason.trim() || undefined);
      setReason('');
      onOpenChange(false);
    } catch {
      // Error handling is done in the parent component
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!isSubmitting) {
      if (!newOpen) {
        setReason('');
      }
      onOpenChange(newOpen);
    }
  };

  const processing = isLoading || isSubmitting;

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent className="max-w-lg">
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2 text-error-600 dark:text-error-400">
            <AlertTriangle className="h-5 w-5" aria-hidden="true" />
            {t('adminModeration.comments.rejectTitle')}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {t('adminModeration.comments.rejectDescription', { username: authorUsername })}
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="space-y-4 py-2">
          {/* Comment content preview */}
          <div>
            <Label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
              {t('adminModeration.comments.contentToReject')}
            </Label>
            <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-3 max-h-32 overflow-y-auto border border-gray-200 dark:border-gray-700">
              <RichTextDisplay
                content={commentContent}
                className="text-sm text-gray-800 dark:text-gray-200"
              />
            </div>
          </div>

          {/* Optional rejection reason */}
          <div>
            <Label
              htmlFor="rejection-reason"
              className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block"
            >
              {t('adminModeration.comments.rejectionReason')}{' '}
              <span className="text-gray-400 font-normal">({t('common.optional')})</span>
            </Label>
            <Textarea
              id="rejection-reason"
              value={reason}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setReason(e.target.value)}
              placeholder={t('adminModeration.comments.rejectionReasonPlaceholder')}
              className="resize-none"
              rows={3}
              disabled={processing}
            />
          </div>
        </div>

        <AlertDialogFooter>
          <AlertDialogCancel disabled={processing}>{t('common.cancel')}</AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            disabled={processing}
            className="bg-error-500 hover:bg-error-600 focus:ring-error-500"
          >
            {processing ? t('common.processing') : t('admin.reject')}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
