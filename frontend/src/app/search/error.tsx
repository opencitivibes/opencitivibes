'use client';

import { useEffect } from 'react';
import { captureException } from '@/lib/sentry-utils';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/Button';

export default function SearchError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useTranslation();

  useEffect(() => {
    captureException(error, {
      tags: { section: 'search' },
    });
  }, [error]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="max-w-md w-full text-center">
        {/* Error icon */}
        <div className="mx-auto w-16 h-16 bg-error-100 dark:bg-error-900/30 rounded-full flex items-center justify-center mb-6">
          <svg
            className="w-8 h-8 text-error-600 dark:text-error-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          {t('errors.searchError', 'Search Error')}
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          {t(
            'errors.searchErrorDescription',
            'An error occurred while searching. Please try again with different terms.'
          )}
        </p>

        {error.digest && (
          <p className="text-xs text-gray-400 dark:text-gray-500 mb-4 font-mono">
            Reference: {error.digest}
          </p>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Button onClick={reset} variant="primary">
            {t('errors.tryAgain', 'Try again')}
          </Button>
          <Button onClick={() => (window.location.href = '/')} variant="secondary">
            {t('errors.goHome', 'Go home')}
          </Button>
        </div>
      </div>
    </div>
  );
}
