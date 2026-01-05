import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Common search engine crawler user agents
const CRAWLER_PATTERNS = [
  'googlebot',
  'bingbot',
  'yandexbot',
  'duckduckbot',
  'baiduspider',
  'facebot',
  'twitterbot',
  'linkedinbot',
  'slurp',
];

function isCrawler(userAgent: string): boolean {
  const ua = userAgent.toLowerCase();
  return CRAWLER_PATTERNS.some((pattern) => ua.includes(pattern));
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const response = NextResponse.next();

  // Get user agent
  const userAgent = request.headers.get('user-agent') || '';

  // For crawlers, add content-language header
  // This helps search engines understand the bilingual nature
  if (isCrawler(userAgent)) {
    response.headers.set('Content-Language', 'fr-CA, en-CA');
  }

  // Redirect trailing slashes (except root)
  if (pathname !== '/' && pathname.endsWith('/')) {
    const newUrl = new URL(pathname.slice(0, -1) + search, request.url);
    return NextResponse.redirect(newUrl, 308);
  }

  // Handle legacy URL patterns if any
  // Example: /idea/123 -> /ideas/123
  if (pathname.startsWith('/idea/') && !pathname.startsWith('/ideas/')) {
    const id = pathname.replace('/idea/', '');
    const newUrl = new URL(`/ideas/${id}${search}`, request.url);
    return NextResponse.redirect(newUrl, 308);
  }

  return response;
}

export const config = {
  matcher: [
    // Match all paths except static files and API
    '/((?!api|_next/static|_next/image|favicon.ico|images|icons).*)',
  ],
};
