'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { ChevronLeft, Shield, Check, X, Mail, History, ChevronDown, ChevronUp } from 'lucide-react';
import { authAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Alert } from '@/components/Alert';
import { useToast } from '@/hooks/useToast';
import Link from 'next/link';
import type { ConsentStatus, ConsentLogEntry } from '@/types';

export default function ConsentManagementPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { user } = useAuthStore();
  const { success, error: showError } = useToast();

  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [consentStatus, setConsentStatus] = useState<ConsentStatus | null>(null);
  const [consentHistory, setConsentHistory] = useState<ConsentLogEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Redirect if not logged in
  useEffect(() => {
    if (!user) {
      router.push('/signin?redirect=/settings/consent');
    }
  }, [user, router]);

  // Fetch consent status
  useEffect(() => {
    const fetchConsent = async () => {
      try {
        const status = await authAPI.getConsentStatus();
        setConsentStatus(status);
      } catch {
        showError(t('settings.consent.error'));
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      fetchConsent();
    }
  }, [user, showError, t]);

  const handleMarketingToggle = async () => {
    if (!consentStatus) return;

    setUpdating(true);
    try {
      const newStatus = await authAPI.updateConsent({
        marketing_consent: !consentStatus.marketing_consent,
      });
      setConsentStatus(newStatus);
      success(t('settings.consent.updated'));
      // Refresh history after consent change
      if (showHistory) {
        const history = await authAPI.getConsentHistory();
        setConsentHistory(history);
      }
    } catch {
      showError(t('settings.consent.error'));
    } finally {
      setUpdating(false);
    }
  };

  const handleToggleHistory = async () => {
    if (!showHistory && consentHistory.length === 0) {
      setHistoryLoading(true);
      try {
        const history = await authAPI.getConsentHistory();
        setConsentHistory(history);
      } catch {
        showError(t('settings.consent.historyError'));
      } finally {
        setHistoryLoading(false);
      }
    }
    setShowHistory(!showHistory);
  };

  if (!user) return null;

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <PageContainer maxWidth="2xl" paddingY="normal">
      <div className="mb-6">
        <Link
          href="/profile"
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          {t('common.back')}
        </Link>
      </div>

      <PageHeader
        title={t('settings.consent.title')}
        description={t('settings.consent.description')}
      />

      {loading ? (
        <Card className="mt-6 animate-pulse">
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded" />
        </Card>
      ) : consentStatus ? (
        <>
          <Card className="mt-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5" />
              {t('settings.consent.currentStatus')}
            </h2>

            {/* Terms of Service */}
            <div className="border-b border-gray-200 dark:border-gray-700 pb-4 mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {consentStatus.terms_accepted ? (
                    <Check className="w-5 h-5 text-green-500" />
                  ) : (
                    <X className="w-5 h-5 text-red-500" />
                  )}
                  <div>
                    <p className="font-medium">{t('settings.consent.termsAccepted')}</p>
                    <p className="text-sm text-gray-500">
                      {t('settings.consent.version')}: {consentStatus.terms_version || '-'}
                    </p>
                  </div>
                </div>
                <span className="text-xs px-2 py-1 bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 rounded">
                  {t('settings.consent.required')}
                </span>
              </div>
            </div>

            {/* Privacy Policy */}
            <div className="border-b border-gray-200 dark:border-gray-700 pb-4 mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {consentStatus.privacy_accepted ? (
                    <Check className="w-5 h-5 text-green-500" />
                  ) : (
                    <X className="w-5 h-5 text-red-500" />
                  )}
                  <div>
                    <p className="font-medium">{t('settings.consent.privacyAccepted')}</p>
                    <p className="text-sm text-gray-500">
                      {t('settings.consent.version')}: {consentStatus.privacy_version || '-'}
                    </p>
                  </div>
                </div>
                <span className="text-xs px-2 py-1 bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300 rounded">
                  {t('settings.consent.required')}
                </span>
              </div>
            </div>

            {/* Marketing Consent */}
            <div className="pb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail className="w-5 h-5 text-gray-400" />
                  <div>
                    <p className="font-medium">{t('settings.consent.marketingConsent')}</p>
                    <p className="text-sm text-gray-500">
                      {t('settings.consent.marketingDescription')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 rounded">
                    {t('settings.consent.optional')}
                  </span>
                  <Button
                    size="sm"
                    variant={consentStatus.marketing_consent ? 'secondary' : 'primary'}
                    onClick={handleMarketingToggle}
                    disabled={updating}
                    loading={updating}
                  >
                    {consentStatus.marketing_consent
                      ? t('settings.consent.withdraw')
                      : t('settings.consent.grant')}
                  </Button>
                </div>
              </div>
            </div>

            {/* Consent timestamp */}
            {consentStatus.consent_timestamp && (
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <p className="text-sm text-gray-500">
                  {t('settings.consent.consentedOn')}: {formatDate(consentStatus.consent_timestamp)}
                </p>
              </div>
            )}
          </Card>

          {/* Warning about withdrawing required consents */}
          <Alert variant="warning" className="mt-6">
            {t('settings.consent.withdrawWarning')}
          </Alert>

          {/* Consent History Section */}
          <Card className="mt-6">
            <button
              onClick={handleToggleHistory}
              className="w-full flex items-center justify-between text-left"
              disabled={historyLoading}
            >
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <History className="w-5 h-5" />
                {t('settings.consent.historyTitle')}
              </h2>
              {historyLoading ? (
                <div className="w-5 h-5 border-2 border-gray-300 border-t-primary-600 rounded-full animate-spin" />
              ) : showHistory ? (
                <ChevronUp className="w-5 h-5 text-gray-500" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-500" />
              )}
            </button>

            {showHistory && (
              <div className="mt-4 space-y-3">
                {consentHistory.length === 0 ? (
                  <p className="text-sm text-gray-500">{t('settings.consent.noHistory')}</p>
                ) : (
                  consentHistory.map((entry, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-800 last:border-0"
                    >
                      <div className="flex items-center gap-3">
                        {entry.action === 'granted' || entry.action === 'updated' ? (
                          <Check className="w-4 h-4 text-green-500" />
                        ) : (
                          <X className="w-4 h-4 text-red-500" />
                        )}
                        <div>
                          <p className="text-sm font-medium">
                            {t(`settings.consent.types.${entry.consent_type}`, entry.consent_type)}
                          </p>
                          <p className="text-xs text-gray-500">
                            {t(`settings.consent.actions.${entry.action}`, entry.action)}
                            {entry.policy_version && ` (v${entry.policy_version})`}
                          </p>
                        </div>
                      </div>
                      <span className="text-xs text-gray-400">{formatDate(entry.created_at)}</span>
                    </div>
                  ))
                )}
              </div>
            )}
          </Card>
        </>
      ) : (
        <Alert variant="error" className="mt-6">
          {t('settings.consent.error')}
        </Alert>
      )}

      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          {t('settings.consent.law25Notice')}
        </p>
      </div>

      <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700 flex gap-4">
        <Link
          href="/settings/data"
          className="text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400"
        >
          {t('settings.data.title')}
        </Link>
        <Link
          href="/settings/delete-account"
          className="text-sm text-red-600 hover:text-red-700 dark:text-red-400"
        >
          {t('settings.delete.title')}
        </Link>
      </div>
    </PageContainer>
  );
}
