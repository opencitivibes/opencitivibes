import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Validates that a redirect URL is safe (relative path only).
 * Prevents open redirect vulnerabilities.
 */
export function isValidRedirect(url: string): boolean {
  // Must start with / (relative path)
  if (!url.startsWith('/')) return false;
  // Prevent protocol-relative URLs (//evil.com)
  if (url.startsWith('//')) return false;
  // Prevent javascript: and data: URIs
  if (/^(javascript|data):/i.test(url)) return false;
  return true;
}

/**
 * Returns a safe redirect URL, defaulting to '/' if invalid.
 */
export function getSafeRedirect(url: string | null): string {
  if (!url) return '/';
  return isValidRedirect(url) ? url : '/';
}
