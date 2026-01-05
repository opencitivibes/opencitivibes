'use client';

import { captureException } from '@/lib/sentry-utils';
import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Capture error in Sentry (no-op if Sentry disabled)
    captureException(error);
  }, [error]);

  return (
    <html>
      <body>
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-4">Something went wrong</h2>
            <p className="text-muted-foreground mb-4">
              We&apos;ve been notified and are working on it.
            </p>
            {error.digest && (
              <p className="text-sm text-muted-foreground mb-4">Reference: {error.digest}</p>
            )}
            <button
              onClick={reset}
              className="px-4 py-2 bg-primary text-primary-foreground rounded"
            >
              Try again
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
