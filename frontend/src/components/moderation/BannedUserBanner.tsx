'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { formatDistanceToNow } from 'date-fns';
import { getDateFnsLocale } from '@/lib/i18n-helpers';
import { Alert } from '@/components/Alert';
import { Button } from '@/components/Button';
import type { PenaltyResponse } from '@/types/moderation';
import { AppealForm } from './AppealForm';

interface BannedUserBannerProps {
  penalty: PenaltyResponse;
  onAppealSubmitted?: () => void;
}

export function BannedUserBanner({ penalty, onAppealSubmitted }: BannedUserBannerProps) {
  const { t, i18n } = useTranslation();
  const [showAppealForm, setShowAppealForm] = useState(false);
  const [timeRemaining, setTimeRemaining] = useState<string>('');

  const locale = getDateFnsLocale(i18n.language);

  // Calculate time remaining for temp bans
  useEffect(() => {
    if (!penalty.expires_at) return;

    const updateTimeRemaining = () => {
      const expiresAt = new Date(penalty.expires_at!);
      if (expiresAt > new Date()) {
        setTimeRemaining(formatDistanceToNow(expiresAt, { addSuffix: true, locale }));
      } else {
        setTimeRemaining(t('moderation.expired'));
      }
    };

    updateTimeRemaining();
    const interval = setInterval(updateTimeRemaining, 60000); // Update every minute

    return () => clearInterval(interval);
  }, [penalty.expires_at, locale, t]);

  const getPenaltyLabel = () => {
    return t(`moderation.penaltyTypes.${penalty.penalty_type}`);
  };

  const canAppeal = penalty.status === 'active' && penalty.penalty_type !== 'warning';

  return (
    <>
      <Alert variant="error" className="mb-4">
        <div className="flex items-start gap-3">
          <svg
            className="h-5 w-5 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
            />
          </svg>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold">{t('moderation.accountSuspended')}</span>
              <span className="text-sm font-normal">({getPenaltyLabel()})</span>
            </div>
            <p className="text-sm mb-2">{penalty.reason}</p>

            {penalty.expires_at && (
              <p className="flex items-center gap-1 text-sm">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                {t('moderation.expiresIn', { time: timeRemaining })}
              </p>
            )}

            {!penalty.expires_at && (
              <p className="text-sm font-medium">{t('moderation.permanentBan')}</p>
            )}

            {canAppeal && !showAppealForm && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowAppealForm(true)}
                className="mt-2"
              >
                {t('moderation.submitAppeal')}
              </Button>
            )}
          </div>
        </div>
      </Alert>

      {showAppealForm && (
        <AppealForm
          penaltyId={penalty.id}
          onClose={() => setShowAppealForm(false)}
          onSubmitted={() => {
            setShowAppealForm(false);
            onAppealSubmitted?.();
          }}
        />
      )}
    </>
  );
}
