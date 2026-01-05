export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    await import('./sentry.server.config');
  }

  if (process.env.NEXT_RUNTIME === 'edge') {
    await import('./sentry.edge.config');
  }
}

export const onRequestError = async (
  err: Error,
  request: { path: string; method: string; headers: Record<string, string> },
  context: {
    routerKind: string;
    routeType: string;
    routePath: string;
    revalidateReason?: string;
  }
) => {
  // Skip if Sentry is not configured
  if (!process.env.NEXT_PUBLIC_SENTRY_DSN) return;

  const Sentry = await import('@sentry/nextjs');
  Sentry.captureException(err, {
    extra: {
      request_path: request.path,
      request_method: request.method,
      router_kind: context.routerKind,
      route_type: context.routeType,
      route_path: context.routePath,
    },
  });
};
