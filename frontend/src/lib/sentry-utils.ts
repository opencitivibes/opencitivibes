/**
 * Sentry utility wrappers that conditionally execute Sentry APIs.
 * When NEXT_PUBLIC_SENTRY_DSN is not set, all functions are no-ops.
 * This ensures the application works correctly without Sentry configured.
 */
import * as Sentry from '@sentry/nextjs';

/**
 * Whether Sentry is enabled (DSN is configured)
 */
export const isSentryEnabled = !!process.env.NEXT_PUBLIC_SENTRY_DSN;

/**
 * Capture an exception in Sentry (no-op if Sentry disabled)
 */
export function captureException(
  error: Error | unknown,
  captureContext?: Sentry.CaptureContext
): string | undefined {
  if (!isSentryEnabled) return undefined;
  return Sentry.captureException(error, captureContext);
}

/**
 * Capture a message in Sentry (no-op if Sentry disabled)
 */
export function captureMessage(
  message: string,
  captureContext?: Sentry.CaptureContext | Sentry.SeverityLevel
): string | undefined {
  if (!isSentryEnabled) return undefined;
  return Sentry.captureMessage(message, captureContext);
}

/**
 * Set the current user in Sentry (no-op if Sentry disabled)
 */
export function setUser(user: Sentry.User | null): void {
  if (!isSentryEnabled) return;
  Sentry.setUser(user);
}

/**
 * Set a tag in Sentry (no-op if Sentry disabled)
 */
export function setTag(key: string, value: string): void {
  if (!isSentryEnabled) return;
  Sentry.setTag(key, value);
}

/**
 * Execute a callback with a Sentry scope (no-op if Sentry disabled)
 */
export function withScope(callback: (scope: Sentry.Scope) => void): void {
  if (!isSentryEnabled) return;
  Sentry.withScope(callback);
}

/**
 * Get the active span (returns undefined if Sentry disabled)
 */
export function getActiveSpan(): Sentry.Span | undefined {
  if (!isSentryEnabled) return undefined;
  return Sentry.getActiveSpan();
}

/**
 * Start a span and execute a callback (executes callback directly if Sentry disabled)
 */
export function startSpan<T>(
  context: Parameters<typeof Sentry.startSpan>[0],
  callback: (span: Sentry.Span | undefined) => T
): T {
  if (!isSentryEnabled) {
    return callback(undefined);
  }
  return Sentry.startSpan(context, callback);
}

// Re-export types that consumers might need
export type { User as SentryUser, Span, CaptureContext, SeverityLevel } from '@sentry/nextjs';
