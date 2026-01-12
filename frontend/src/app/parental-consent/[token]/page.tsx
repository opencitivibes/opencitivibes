'use client';

import { useState, useEffect, use } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { parentalConsentAPI } from '@/lib/api';
import { Button } from '@/components/Button';
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
import type { ParentalConsentDetails, ConsentErrorType } from '@/types';

interface PageProps {
  params: Promise<{ token: string }>;
}

export default function ParentalConsentPage({ params }: PageProps) {
  const { token } = use(params);
  const { t } = useTranslation();
  const router = useRouter();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [details, setDetails] = useState<ParentalConsentDetails | null>(null);
  const [error, setError] = useState<ConsentErrorType | null>(null);
  const [showDenyDialog, setShowDenyDialog] = useState(false);

  useEffect(() => {
    async function verifyToken() {
      try {
        const data = await parentalConsentAPI.verify(token);
        setDetails(data);
      } catch (err: unknown) {
        // Determine error type from response using backend type field
        const errorResponse = err as { response?: { data?: { type?: string } } };
        const backendType = errorResponse.response?.data?.type;

        if (backendType === 'consent_token_expired') {
          setError('expired');
        } else if (backendType === 'consent_already_processed') {
          setError('used');
        } else {
          // consent_token_not_found or any other error
          setError('invalid');
        }
      } finally {
        setLoading(false);
      }
    }

    verifyToken();
  }, [token]);

  const handleGrant = async () => {
    setSubmitting(true);
    try {
      await parentalConsentAPI.grant(token);
      router.push('/parental-consent/success?action=granted');
    } catch {
      // Error toast is shown by api interceptor
      setSubmitting(false);
    }
  };

  const handleDeny = async () => {
    setSubmitting(true);
    try {
      await parentalConsentAPI.deny(token);
      router.push('/parental-consent/denied');
    } catch {
      // Error toast is shown by api interceptor
      setSubmitting(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(t('consent.dateLocale'), {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  // Loading state
  if (loading) {
    return (
      <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
            <div className="flex items-center justify-center">
              <svg
                className="animate-spin h-8 w-8 text-primary-500"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-label={t('common.loading')}
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              <span className="ml-3 text-gray-600 dark:text-gray-400">
                {t('consent.verifying')}
              </span>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // Error state
  if (error) {
    router.push(`/parental-consent/error?type=${error}`);
    return null;
  }

  // Success - show consent details
  if (!details) {
    return null;
  }

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
          {/* Header */}
          <header className="bg-primary-600 dark:bg-primary-700 px-6 py-8 text-center">
            <h1 className="text-2xl md:text-3xl font-bold text-white">{t('consent.pageTitle')}</h1>
            <p className="mt-2 text-primary-100">{t('consent.subtitle')}</p>
          </header>

          <div className="p-6 md:p-8 space-y-6">
            {/* Child Information */}
            <section aria-labelledby="child-info-heading">
              <h2
                id="child-info-heading"
                className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center"
              >
                <span className="w-8 h-8 bg-primary-100 dark:bg-primary-900 rounded-full flex items-center justify-center mr-3">
                  <svg
                    className="w-4 h-4 text-primary-600 dark:text-primary-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                </span>
                {t('consent.childInfo')}
              </h2>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">{t('consent.username')}</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {details.child_username}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">{t('consent.email')}</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {details.child_email}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600 dark:text-gray-400">{t('consent.age')}</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {t('consent.yearsOld', { age: details.child_age })}
                  </span>
                </div>
              </div>
            </section>

            {/* Data Collected */}
            <section aria-labelledby="data-collected-heading">
              <h2
                id="data-collected-heading"
                className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center"
              >
                <span className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mr-3">
                  <svg
                    className="w-4 h-4 text-blue-600 dark:text-blue-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </span>
                {t('consent.dataCollected')}
              </h2>
              <ul className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-2">
                <li className="flex items-start">
                  <span className="text-blue-500 mr-2" aria-hidden="true">
                    •
                  </span>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('consent.dataCollectedItems.email')}
                  </span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-500 mr-2" aria-hidden="true">
                    •
                  </span>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('consent.dataCollectedItems.content')}
                  </span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-500 mr-2" aria-hidden="true">
                    •
                  </span>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('consent.dataCollectedItems.activity')}
                  </span>
                </li>
                <li className="flex items-start">
                  <span className="text-blue-500 mr-2" aria-hidden="true">
                    •
                  </span>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('consent.dataCollectedItems.security')}
                  </span>
                </li>
              </ul>
            </section>

            {/* Purpose & Retention */}
            <section aria-labelledby="purpose-heading">
              <h2
                id="purpose-heading"
                className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center"
              >
                <span className="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mr-3">
                  <svg
                    className="w-4 h-4 text-green-600 dark:text-green-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </span>
                {t('consent.purposeTitle')}
              </h2>
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-3">
                <div>
                  <span className="text-sm text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    {t('consent.purpose')}
                  </span>
                  <p className="text-gray-700 dark:text-gray-300 mt-1">
                    {t('consent.purposeText')}
                  </p>
                </div>
                <div>
                  <span className="text-sm text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                    {t('consent.retention')}
                  </span>
                  <p className="text-gray-700 dark:text-gray-300 mt-1">
                    {t('consent.retentionText')}
                  </p>
                </div>
              </div>
            </section>

            {/* Parent Rights */}
            <section aria-labelledby="rights-heading">
              <h2
                id="rights-heading"
                className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center"
              >
                <span className="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-full flex items-center justify-center mr-3">
                  <svg
                    className="w-4 h-4 text-purple-600 dark:text-purple-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    />
                  </svg>
                </span>
                {t('consent.parentRights')}
              </h2>
              <ul className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-2">
                <li className="flex items-start">
                  <svg
                    className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('consent.rights.access')}
                  </span>
                </li>
                <li className="flex items-start">
                  <svg
                    className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('consent.rights.rectify')}
                  </span>
                </li>
                <li className="flex items-start">
                  <svg
                    className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('consent.rights.delete')}
                  </span>
                </li>
                <li className="flex items-start">
                  <svg
                    className="w-5 h-5 text-green-500 mr-2 flex-shrink-0 mt-0.5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  <span className="text-gray-700 dark:text-gray-300">
                    {t('consent.rights.withdraw')}
                  </span>
                </li>
              </ul>
            </section>

            {/* Expiration Warning */}
            <div
              className="flex items-center p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg"
              role="alert"
            >
              <svg
                className="w-5 h-5 text-amber-500 mr-3 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span className="text-amber-800 dark:text-amber-200">
                {t('consent.expiresIn', { date: formatDate(details.expires_at) })}
              </span>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 pt-4">
              <Button
                variant="primary"
                size="lg"
                className="flex-1"
                onClick={handleGrant}
                loading={submitting}
                disabled={submitting}
                aria-describedby="grant-description"
              >
                {t('consent.grantButton')}
              </Button>
              <Button
                variant="secondary"
                size="lg"
                className="flex-1"
                onClick={() => setShowDenyDialog(true)}
                disabled={submitting}
                aria-describedby="deny-description"
              >
                {t('consent.denyButton')}
              </Button>
            </div>
            <p id="grant-description" className="sr-only">
              {t('consent.grantDescription')}
            </p>
            <p id="deny-description" className="sr-only">
              {t('consent.denyDescription')}
            </p>
          </div>
        </div>
      </div>

      {/* Deny Confirmation Dialog */}
      <AlertDialog open={showDenyDialog} onOpenChange={setShowDenyDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('consent.denyConfirm.title')}</AlertDialogTitle>
            <AlertDialogDescription>{t('consent.denyConfirm.message')}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={submitting}>
              {t('consent.denyConfirm.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeny}
              disabled={submitting}
              className="bg-red-600 hover:bg-red-700 focus:ring-red-500"
            >
              {submitting ? t('common.processing') : t('consent.denyConfirm.confirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}
