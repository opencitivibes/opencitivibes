import { siteConfig } from './metadata';

/**
 * Generate canonical URL for a given path.
 * Handles trailing slashes, query parameters, and fragments.
 */
export function getCanonicalUrl(path: string): string {
  // Remove trailing slash (except for root)
  const normalizedPath = path === '/' ? '/' : path.replace(/\/$/, '');

  // Remove query parameters and fragments for canonical
  const cleanPath = (normalizedPath.split('?')[0] ?? '').split('#')[0] ?? '';

  return `${siteConfig.url}${cleanPath}`;
}

/**
 * Generate alternate URLs for different languages.
 */
export function getAlternateUrls(path: string): {
  'fr-CA': string;
  'en-CA': string;
  'x-default': string;
} {
  const canonicalPath = path === '/' ? '' : path.replace(/\/$/, '');

  return {
    'fr-CA': `${siteConfig.url}${canonicalPath}`,
    'en-CA': `${siteConfig.url}${canonicalPath}`,
    'x-default': `${siteConfig.url}${canonicalPath}`,
  };
}

/**
 * Check if a URL should be indexed.
 */
export function shouldIndex(path: string): boolean {
  const noIndexPaths = ['/admin', '/my-ideas', '/profile', '/signin', '/signup'];

  return !noIndexPaths.some((noIndex) => path.startsWith(noIndex));
}
