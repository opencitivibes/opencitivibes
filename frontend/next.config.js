const { withSentryConfig } = require('@sentry/nextjs');
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

/** @type {import('next').NextConfig} */

// Security headers configuration
const securityHeaders = [
  {
    key: 'X-DNS-Prefetch-Control',
    value: 'on',
  },
  {
    key: 'X-XSS-Protection',
    value: '1; mode=block',
  },
  {
    key: 'X-Frame-Options',
    value: 'SAMEORIGIN',
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff',
  },
  {
    key: 'Referrer-Policy',
    value: 'origin-when-cross-origin',
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=()',
  },
  {
    key: 'Content-Security-Policy',
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-eval' 'unsafe-inline' https://static.cloudflareinsights.com https://*.cloudflareinsights.com",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob: https:",
      "font-src 'self' data:",
      // Allow API connections: in dev mode allow all http/https, in prod restrict to known domains
      process.env.NODE_ENV === 'development'
        ? "connect-src 'self' http: https:"
        : "connect-src 'self' https://*.idees-montreal.ca https://*.idees-quebec.ca https://*.ideas-calgary.ca https://*.opencitivibes.ovh https://*.sentry.io https://cloudflareinsights.com https://*.cloudflareinsights.com",
      "worker-src 'self' blob:",
      "frame-ancestors 'self'",
      "form-action 'self'",
      "base-uri 'self'",
      "object-src 'none'",
    ].join('; '),
  },
];

// SEO-related headers
const seoHeaders = [
  {
    key: 'X-Robots-Tag',
    value: 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1',
  },
];

// Cache control headers for static assets
const cacheHeaders = [
  {
    key: 'Cache-Control',
    value: 'public, max-age=31536000, immutable',
  },
];

// Cache control for public pages (enables Cloudflare edge caching)
const pagesCacheHeaders = [
  {
    key: 'Cache-Control',
    value: 'public, s-maxage=3600, stale-while-revalidate=86400',
  },
];

// No-index header for private routes
const noIndexHeaders = [
  {
    key: 'X-Robots-Tag',
    value: 'noindex, nofollow',
  },
];

const nextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',

  reactStrictMode: true,

  // Allow dev server access from local network IPs (mobile testing)
  // Format: hostname or hostname:port (NO protocol prefix)
  allowedDevOrigins: ['192.168.0.65', '192.168.0.65:3000'],

  // Image optimization for Core Web Vitals
  images: {
    // Enable modern formats for better compression
    formats: ['image/avif', 'image/webp'],
    // Define device sizes for responsive images
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    // Security settings
    dangerouslyAllowSVG: false,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },

  // Apply headers to routes
  async headers() {
    return [
      {
        // Apply security and SEO headers to all routes
        source: '/:path*',
        headers: [...securityHeaders, ...seoHeaders],
      },
      {
        // Cache static assets aggressively
        source: '/images/:path*',
        headers: cacheHeaders,
      },
      {
        source: '/_next/static/:path*',
        headers: cacheHeaders,
      },
      {
        // Enable edge caching for homepage (public, dynamic content fetched client-side)
        source: '/',
        headers: pagesCacheHeaders,
      },
      {
        // Enable edge caching for idea detail pages (SEO important, content fetched client-side)
        source: '/ideas/:id*',
        headers: pagesCacheHeaders,
      },
      {
        // Enable edge caching for category pages
        source: '/categories/:path*',
        headers: pagesCacheHeaders,
      },
      {
        // No-index for admin routes
        source: '/admin/:path*',
        headers: noIndexHeaders,
      },
      {
        // No-index for authenticated routes
        source: '/my-ideas',
        headers: noIndexHeaders,
      },
      {
        source: '/profile',
        headers: noIndexHeaders,
      },
    ];
  },

  // Redirects for SEO
  async redirects() {
    return [
      // Redirect trailing slashes (except root)
      {
        source: '/:path+/',
        destination: '/:path+',
        permanent: true,
      },
    ];
  },

  // Rewrites to proxy static uploads through frontend (fixes SSR hydration mismatch)
  async rewrites() {
    // In development, use localhost; in production, use env var or localhost
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    return [
      {
        source: '/uploads/:path*',
        destination: `${backendUrl}/data/uploads/:path*`,
      },
    ];
  },
};

// Sentry configuration
const sentryWebpackPluginOptions = {
  // Organization and project from Sentry
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,

  // Silences source map uploading logs during build
  silent: true,

  // Upload source maps for production only
  sourcemaps: {
    disable: process.env.NODE_ENV !== 'production',
  },

  // Hides source maps from generated client bundles
  hideSourceMaps: true,

  // Automatically tree-shake Sentry logger statements
  bundleSizeOptimizations: {
    excludeDebugStatements: true,
  },

  // Auth token for source map uploads (CI/CD only)
  authToken: process.env.SENTRY_AUTH_TOKEN,
};

// Wrap config with Bundle Analyzer, and optionally Sentry if DSN is configured
const configWithAnalyzer = withBundleAnalyzer(nextConfig);

// Only wrap with Sentry if DSN is configured (reduces build overhead when disabled)
module.exports = process.env.NEXT_PUBLIC_SENTRY_DSN
  ? withSentryConfig(configWithAnalyzer, sentryWebpackPluginOptions)
  : configWithAnalyzer;
