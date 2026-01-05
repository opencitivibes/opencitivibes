'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/Button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/Textarea';
import { Alert } from '@/components/Alert';
import type { ContentType, FlagReason } from '@/types/moderation';

interface FlagDialogProps {
  contentType: ContentType;
  contentPreview: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (reason: FlagReason, details?: string) => Promise<void>;
  isLoading: boolean;
}

const FLAG_REASONS: FlagReason[] = [
  'spam',
  'hate_speech',
  'harassment',
  'off_topic',
  'misinformation',
  'other',
];

export function FlagDialog({
  contentType,
  contentPreview,
  isOpen,
  onClose,
  onSubmit,
  isLoading,
}: FlagDialogProps) {
  const { t } = useTranslation();
  const [selectedReason, setSelectedReason] = useState<FlagReason | null>(null);
  const [details, setDetails] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!selectedReason) {
      setError(t('moderation.selectReasonError'));
      return;
    }

    if (selectedReason === 'other' && !details.trim()) {
      setError(t('moderation.provideDetailsError'));
      return;
    }

    setError(null);
    try {
      await onSubmit(selectedReason, details.trim() || undefined);
    } catch {
      setError(t('moderation.submitError'));
    }
  };

  const handleClose = () => {
    setSelectedReason(null);
    setDetails('');
    setError(null);
    onClose();
  };

  const getReasonLabel = (reason: FlagReason) => {
    return t(`moderation.reasons.${reason}`);
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-error-600 dark:text-error-400">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            {t('moderation.reportTitle', {
              type: contentType === 'comment' ? t('moderation.comment') : t('moderation.idea'),
            })}
          </DialogTitle>
          <DialogDescription>{t('moderation.reportDescription')}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Content preview */}
          <div className="rounded-md bg-gray-100 dark:bg-gray-700 p-3">
            <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-3">
              {contentPreview}
            </p>
          </div>

          {/* Reason selection */}
          <div className="space-y-3">
            <Label className="text-base font-medium text-gray-900 dark:text-gray-100">
              {t('moderation.selectReason')}
            </Label>
            <RadioGroup
              value={selectedReason || ''}
              onValueChange={(value) => setSelectedReason(value as FlagReason)}
            >
              {FLAG_REASONS.map((reason) => (
                <div key={reason} className="flex items-center space-x-2">
                  <RadioGroupItem value={reason} id={reason} />
                  <Label
                    htmlFor={reason}
                    className="font-normal cursor-pointer text-gray-700 dark:text-gray-300"
                  >
                    {getReasonLabel(reason)}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </div>

          {/* Details textarea */}
          <div className="space-y-2">
            <Label htmlFor="details" className="text-gray-700 dark:text-gray-300">
              {t('moderation.additionalDetails')}
              {selectedReason === 'other' && (
                <span className="text-error-500 dark:text-error-400"> *</span>
              )}
            </Label>
            <Textarea
              id="details"
              placeholder={t('moderation.detailsPlaceholder')}
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              maxLength={500}
              rows={3}
            />
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {details.length}/500 {t('common.characters')}
            </p>
          </div>

          {error && <Alert variant="error">{error}</Alert>}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={handleClose} disabled={isLoading}>
            {t('common.cancel')}
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={isLoading || !selectedReason}
            loading={isLoading}
            className="bg-error-500 hover:bg-error-600 active:bg-error-700 focus:ring-error-500 dark:bg-error-600 dark:hover:bg-error-500"
          >
            {t('moderation.submitReport')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
