'use client';

import { useSearchParams } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import Link from 'next/link';
import { Button } from '@/components/Button';
import { Suspense } from 'react';

function SuccessContent() {
  const { t } = useTranslation();
  const searchParams = useSearchParams();
  const action = searchParams.get('action') || 'granted';
  const username = searchParams.get('username') || '';

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4">
      <div className="max-w-lg mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
          {/* Success Icon */}
          <div className="mx-auto w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mb-6">
            <svg
              className="w-8 h-8 text-green-600 dark:text-green-400"
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
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            {t('consent.success.granted.title')}
          </h1>

          {/* Message */}
          <p className="text-gray-600 dark:text-gray-400 mb-8">
            {username
              ? t('consent.success.granted.messageWithName', { username })
              : t('consent.success.granted.message')}
          </p>

          {/* What happens next */}
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-8 text-left">
            <h2 className="font-semibold text-gray-900 dark:text-white mb-3">
              {t('consent.success.whatNext')}
            </h2>
            <ul className="space-y-2">
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
                  {action === 'granted'
                    ? t('consent.success.granted.step1')
                    : t('consent.success.step1')}
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
                  {t('consent.success.granted.step2')}
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
                  {t('consent.success.granted.step3')}
                </span>
              </li>
            </ul>
          </div>

          {/* Close Button */}
          <Link href="/">
            <Button variant="primary" size="lg" className="w-full">
              {t('consent.success.closeWindow')}
            </Button>
          </Link>
        </div>
      </div>
    </main>
  );
}

export default function ConsentSuccessPage() {
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
      <SuccessContent />
    </Suspense>
  );
}
