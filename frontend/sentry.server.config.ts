import * as Sentry from '@sentry/nextjs';

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

// Only initialize Sentry if DSN is configured
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,

    environment: process.env.NEXT_PUBLIC_ENVIRONMENT || 'development',
    release: process.env.NEXT_PUBLIC_SENTRY_RELEASE || 'unknown',

    // Privacy
    sendDefaultPii: false,

    // Server-side sampling (same as client)
    tracesSampleRate: 0.2,

    // Breadcrumbs
    maxBreadcrumbs: 50,

    // PII scrubbing
    beforeSend(event) {
      if (event.user?.email) delete event.user.email;
      if (event.user?.username) delete event.user.username;
      return event;
    },
  });
}
