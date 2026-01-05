import * as Sentry from '@sentry/nextjs';
import { errorAPI } from '@/lib/api';

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

// Track if we should notify admin (set by beforeErrorSampling)
let shouldNotifyAdmin = false;

// Only initialize Sentry if DSN is configured
if (SENTRY_DSN) {
  // Expose Sentry globally for console testing (remove in production if desired)
  if (typeof window !== 'undefined') {
    (window as unknown as { Sentry: typeof Sentry }).Sentry = Sentry;
  }

  Sentry.init({
    dsn: SENTRY_DSN,

    // Environment and release tracking
    environment: process.env.NEXT_PUBLIC_ENVIRONMENT || 'development',
    release: process.env.NEXT_PUBLIC_SENTRY_RELEASE || 'unknown',

    // Privacy: Do NOT send PII automatically
    sendDefaultPii: false,

    // Performance monitoring - 20% to stay within free tier limits
    tracesSampleRate: 0.2,

    // Integrations - ensure browser tracing is enabled
    integrations: [
      Sentry.browserTracingIntegration({
        // Instrument XHR/fetch for trace propagation
        enableInp: true,
      }),

      // Session Replay with cost mitigation filter
      Sentry.replayIntegration({
        maskAllText: false,
        blockAllMedia: false,
        maskAllInputs: true,

        // Filter out expected user errors from replay capture (cost mitigation)
        beforeErrorSampling: (event) => {
          const errorMessage = event.exception?.values?.[0]?.value || '';
          const errorType = event.exception?.values?.[0]?.type || '';

          // Skip patterns - expected user errors (not worth debugging with replay)
          const skipPatterns = [
            // Authentication
            /invalid.*credentials/i,
            /incorrect.*password/i,
            /wrong.*password/i,
            // Validation
            /validation.*failed/i,
            /invalid.*input/i,
            /required.*field/i,
            // Rate limiting
            /rate.*limit.*exceeded/i,
            /too.*many.*requests/i,
            // Duplicate actions
            /duplicate.*vote/i,
            /already.*voted/i,
            /already.*flagged/i,
            // Email login codes
            /login.*code.*expired/i,
            /invalid.*login.*code/i,
            /too.*many.*failed.*attempts/i,
            // 2FA
            /invalid.*authentication.*code/i,
            /invalid.*2fa/i,
            /invalid.*totp/i,
            // Not found
            /idea.*not.*found/i,
            /comment.*not.*found/i,
            /user.*not.*found/i,
            /category.*not.*found/i,
            // Already exists
            /already.*exists/i,
            /email.*already.*registered/i,
          ];

          for (const pattern of skipPatterns) {
            if (pattern.test(errorMessage) || pattern.test(errorType)) {
              shouldNotifyAdmin = false; // Low-value error - no notification
              return false; // Skip replay
            }
          }
          shouldNotifyAdmin = true; // High-value error - notify admin
          return true; // Capture replay
        },
      }),
    ],

    // Only trace requests to our API (must include port for localhost)
    tracePropagationTargets: [
      'localhost:8000',
      /^http:\/\/localhost:8000/,
      /^https:\/\/api\.idees-montreal\.ca/,
    ],

    // Session replay - capture on errors only for debugging
    replaysSessionSampleRate: 0, // Don't record normal sessions
    replaysOnErrorSampleRate: 1.0, // Record 100% of error sessions

    // Breadcrumbs configuration
    maxBreadcrumbs: 50,

    // Filter out noisy errors
    ignoreErrors: [
      // Browser extensions
      /^chrome-extension:\/\//,
      /^moz-extension:\/\//,
      // Network errors that are expected
      'Network Error',
      'Request aborted',
      // User-initiated navigation
      'AbortError',
    ],

    // PII scrubbing and admin notification
    beforeSend(event) {
      // Scrub user email if present
      if (event.user?.email) {
        delete event.user.email;
      }
      if (event.user?.username) {
        delete event.user.username;
      }
      // Scrub IP
      if (event.user?.ip_address) {
        event.user.ip_address = '{{auto}}';
      }

      // Notify admin for high-value errors
      if (shouldNotifyAdmin && event.exception?.values?.[0]) {
        const error = event.exception.values[0];
        errorAPI.reportCritical({
          error_type: error.type || 'UnknownError',
          error_message: error.value || 'No message',
          url: typeof window !== 'undefined' ? window.location.href : '',
          sentry_event_id: event.event_id,
        });
        shouldNotifyAdmin = false; // Reset flag
      }

      return event;
    },

    // Filter transactions
    beforeSendTransaction(event) {
      // Skip noisy routes
      const transaction = event.transaction || '';
      if (
        transaction.includes('/_next/') ||
        transaction.includes('/favicon') ||
        transaction === '/health'
      ) {
        return null;
      }
      return event;
    },
  });
}

// Export hook to instrument client-side navigations (no-op if Sentry disabled)
export const onRouterTransitionStart = SENTRY_DSN ? Sentry.captureRouterTransitionStart : () => {};
