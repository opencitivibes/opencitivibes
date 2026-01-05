'use client';

import { useEffect } from 'react';
import { captureException } from '@/lib/sentry-utils';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/Button';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const { t } = useTranslation();

  useEffect(() => {
    // Log the error to Sentry (no-op if Sentry disabled)
    captureException(error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
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
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>

        <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-2">
          {t('errors.somethingWentWrong', 'Something went wrong')}
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          {t(
            'errors.unexpectedError',
            'We encountered an unexpected error. Please try again or contact support if the problem persists.'
          )}
        </p>

        {/* Error digest for debugging */}
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
