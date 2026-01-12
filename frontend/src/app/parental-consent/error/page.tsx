'use client';

import { useSearchParams } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import Link from 'next/link';
import { Button } from '@/components/Button';
import { Suspense } from 'react';
import type { ConsentErrorType } from '@/types';

function ErrorContent() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const errorType = (searchParams.get('type') as ConsentErrorType) || 'invalid';

  const errorConfig = {
    invalid: {
      icon: (
        <svg
          className="w-8 h-8 text-red-600 dark:text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      ),
      bgColor: 'bg-red-100 dark:bg-red-900',
      title: t('consent.error.invalid'),
      message: t('consent.error.invalidMessage'),
      showResend: false,
    },
    expired: {
      icon: (
        <svg
          className="w-8 h-8 text-amber-600 dark:text-amber-400"
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
      ),
      bgColor: 'bg-amber-100 dark:bg-amber-900',
      title: t('consent.error.expired'),
      message: t('consent.error.expiredMessage'),
      showResend: true,
    },
    used: {
      icon: (
        <svg
          className="w-8 h-8 text-blue-600 dark:text-blue-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
      bgColor: 'bg-blue-100 dark:bg-blue-900',
      title: t('consent.error.used'),
      message: t('consent.error.usedMessage'),
      showResend: false,
    },
  };

  const config = errorConfig[errorType] || errorConfig.invalid;

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4">
      <div className="max-w-lg mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
          {/* Icon */}
          <div
            className={`mx-auto w-16 h-16 ${config.bgColor} rounded-full flex items-center justify-center mb-6`}
          >
            {config.icon}
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">{config.title}</h1>

          {/* Message */}
          <p className="text-gray-600 dark:text-gray-400 mb-8">{config.message}</p>

          {/* Actions */}
          <div className="space-y-4">
            {config.showResend && (
              <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4 text-left">
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  {t('consent.error.resendInfo')}
                </p>
              </div>
            )}

            <Link href="/">
              <Button variant="secondary" size="lg" className="w-full">
                {t('consent.error.goHome')}
              </Button>
            </Link>
          </div>

          {/* Contact info */}
          <p className="mt-8 text-sm text-gray-500 dark:text-gray-400">
            {t('consent.error.contactSupport')}
          </p>
        </div>
      </div>
    </main>
  );
}

export default function ConsentErrorPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4">
          <div className="max-w-lg mx-auto">
            <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
              <div className="animate-pulse">
                <div className="mx-auto w-16 h-16 bg-gray-200 dark:bg-gray-700 rounded-full mb-6" />
                <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mx-auto mb-4" />
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-8" />
              </div>
            </div>
          </div>
        </main>
      }
    >
      <ErrorContent />
    </Suspense>
  );
}
