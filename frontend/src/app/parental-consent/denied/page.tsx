'use client';

import { useTranslation } from 'react-i18next';
import Link from 'next/link';
import { Button } from '@/components/Button';

export default function ConsentDeniedPage() {
  const { t } = useTranslation();

  return (
    <main className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12 px-4">
      <div className="max-w-lg mx-auto">
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
          {/* Icon */}
          <div className="mx-auto w-16 h-16 bg-amber-100 dark:bg-amber-900 rounded-full flex items-center justify-center mb-6">
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
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>

          {/* Title */}
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
            {t('consent.success.denied.title')}
          </h1>

          {/* Message */}
          <p className="text-gray-600 dark:text-gray-400 mb-8">
            {t('consent.success.denied.message')}
          </p>

          {/* What happens next */}
          <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-8 text-left">
            <h2 className="font-semibold text-gray-900 dark:text-white mb-3">
              {t('consent.success.whatNext')}
            </h2>
            <ul className="space-y-2">
              <li className="flex items-start">
                <svg
                  className="w-5 h-5 text-amber-500 mr-2 flex-shrink-0 mt-0.5"
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
                <span className="text-gray-700 dark:text-gray-300">
                  {t('consent.success.denied.step1')}
                </span>
              </li>
              <li className="flex items-start">
                <svg
                  className="w-5 h-5 text-amber-500 mr-2 flex-shrink-0 mt-0.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
                <span className="text-gray-700 dark:text-gray-300">
                  {t('consent.success.denied.step2')}
                </span>
              </li>
              <li className="flex items-start">
                <svg
                  className="w-5 h-5 text-amber-500 mr-2 flex-shrink-0 mt-0.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                <span className="text-gray-700 dark:text-gray-300">
                  {t('consent.success.denied.step3')}
                </span>
              </li>
            </ul>
          </div>

          {/* Close Button */}
          <Link href="/">
            <Button variant="secondary" size="lg" className="w-full">
              {t('consent.success.closeWindow')}
            </Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
