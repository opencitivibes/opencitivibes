'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/Button';
import { Textarea } from '@/components/Textarea';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/Alert';
import { moderationAPI } from '@/lib/api';

interface AppealFormProps {
  penaltyId: number;
  onClose: () => void;
  onSubmitted: () => void;
}

export function AppealForm({ penaltyId, onClose, onSubmitted }: AppealFormProps) {
  const { t } = useTranslation();
  const [reason, setReason] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (reason.trim().length < 50) {
      setError(t('moderation.appealMinLength'));
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await moderationAPI.submitAppeal({
        penalty_id: penaltyId,
        reason: reason.trim(),
      });
      setSuccess(true);
      setTimeout(() => {
        onSubmitted();
      }, 2000);
    } catch (err: unknown) {
      const axiosError = err as { response?: { status?: number } };
      if (axiosError.response?.status === 409) {
        setError(t('moderation.appealAlreadyExists'));
      } else {
        setError(t('moderation.appealSubmitError'));
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <Card className="mb-4 border-success-200 bg-success-50">
        <CardContent className="pt-6">
          <p className="text-success-700">{t('moderation.appealSubmitted')}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mb-4">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-lg">{t('moderation.appealTitle')}</CardTitle>
          <CardDescription>{t('moderation.appealDescription')}</CardDescription>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </Button>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="appeal-reason">{t('moderation.appealReason')}</Label>
            <Textarea
              id="appeal-reason"
              placeholder={t('moderation.appealPlaceholder')}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={2000}
              rows={5}
              required
            />
            <p className="text-xs text-gray-500">
              {reason.length}/2000 {t('common.characters')} ({t('moderation.minimum')}: 50)
            </p>
          </div>

          {error && <Alert variant="error">{error}</Alert>}

          <div className="flex gap-2">
            <Button type="button" variant="secondary" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={isLoading || reason.length < 50} loading={isLoading}>
              <svg className="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                />
              </svg>
              {t('moderation.submitAppeal')}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
