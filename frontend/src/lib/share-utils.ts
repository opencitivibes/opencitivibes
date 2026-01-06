/**
 * Share URL utilities for social media sharing.
 * Builds platform-specific share URLs with UTM tracking parameters.
 */

import type { SharePlatform } from '@/types';

/**
 * Add UTM parameters to a URL for tracking.
 */
function addUtmParams(url: string, platform: SharePlatform): string {
  const urlObj = new URL(url);
  urlObj.searchParams.set('utm_source', platform === 'copy_link' ? 'link' : platform);
  urlObj.searchParams.set('utm_medium', 'social');
  urlObj.searchParams.set('utm_campaign', 'idea_share');
  return urlObj.toString();
}

/**
 * Build a Twitter/X share URL.
 * @param url - The URL to share
 * @param text - The tweet text
 */
export function buildTwitterShareUrl(url: string, text: string): string {
  const shareUrl = addUtmParams(url, 'twitter');
  const twitterUrl = new URL('https://twitter.com/intent/tweet');
  twitterUrl.searchParams.set('url', shareUrl);
  twitterUrl.searchParams.set('text', text);
  return twitterUrl.toString();
}

/**
 * Build a Facebook share URL.
 * @param url - The URL to share
 */
export function buildFacebookShareUrl(url: string): string {
  const shareUrl = addUtmParams(url, 'facebook');
  const facebookUrl = new URL('https://www.facebook.com/sharer/sharer.php');
  facebookUrl.searchParams.set('u', shareUrl);
  return facebookUrl.toString();
}

/**
 * Build a LinkedIn share URL.
 * @param url - The URL to share
 */
export function buildLinkedInShareUrl(url: string): string {
  const shareUrl = addUtmParams(url, 'linkedin');
  const linkedInUrl = new URL('https://www.linkedin.com/sharing/share-offsite/');
  linkedInUrl.searchParams.set('url', shareUrl);
  return linkedInUrl.toString();
}

/**
 * Build a WhatsApp share URL.
 * @param url - The URL to share
 * @param text - The message text (URL is appended)
 */
export function buildWhatsAppShareUrl(url: string, text: string): string {
  const shareUrl = addUtmParams(url, 'whatsapp');
  const whatsAppUrl = new URL('https://api.whatsapp.com/send');
  // WhatsApp combines text and URL in one field
  whatsAppUrl.searchParams.set('text', `${text}\n\n${shareUrl}`);
  return whatsAppUrl.toString();
}

/**
 * Copy text to clipboard.
 * @param text - The text to copy
 * @returns Promise that resolves when copy is complete
 */
export async function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    await navigator.clipboard.writeText(text);
  } else {
    // Fallback for older browsers or non-HTTPS
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  }
}

/**
 * Get the shareable URL for the current page with UTM parameters for copy link.
 */
export function getShareableUrl(): string {
  if (typeof window === 'undefined') return '';
  // Get the base URL without any existing UTM params
  const url = new URL(window.location.href);
  // Remove any existing UTM params
  url.searchParams.delete('utm_source');
  url.searchParams.delete('utm_medium');
  url.searchParams.delete('utm_campaign');
  return addUtmParams(url.toString(), 'copy_link');
}

/**
 * Open a share popup window.
 * @param url - The share URL to open
 * @param windowName - Name for the popup window
 */
export function openSharePopup(url: string, windowName = 'share'): void {
  const width = 600;
  const height = 400;
  const left = Math.max(0, (window.innerWidth - width) / 2 + window.screenX);
  const top = Math.max(0, (window.innerHeight - height) / 2 + window.screenY);

  window.open(
    url,
    windowName,
    `width=${width},height=${height},left=${left},top=${top},toolbar=no,menubar=no,scrollbars=yes,resizable=yes`
  );
}
