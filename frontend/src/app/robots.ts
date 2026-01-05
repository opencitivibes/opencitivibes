import { MetadataRoute } from 'next';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://idees-montreal.ca';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: [
          '/admin/', // Admin panel
          '/admin',
          '/my-ideas', // User's private ideas list
          '/profile', // User profile
          '/api/', // API routes (if exposed)
          '/_next/', // Next.js internals
          '/static/', // Static files
          '/*.json$', // JSON files
        ],
      },
      {
        userAgent: 'Googlebot',
        allow: '/',
        disallow: ['/admin/', '/my-ideas', '/profile'],
      },
      {
        // Block aggressive crawlers
        userAgent: 'AhrefsBot',
        crawlDelay: 10,
      },
      {
        userAgent: 'SemrushBot',
        crawlDelay: 10,
      },
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
    host: BASE_URL,
  };
}
