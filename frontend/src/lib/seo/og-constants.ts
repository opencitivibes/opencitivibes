/**
 * Open Graph Image Constants
 *
 * Design tokens for consistent OG image generation.
 * Aligned with BRAND_GUIDELINES.md
 */

// Image dimensions (standard OG image size)
export const OG_WIDTH = 1200;
export const OG_HEIGHT = 630;

// Layout dimensions
export const OG_HEADER_HEIGHT = 60;
export const OG_FOOTER_HEIGHT = 50;
export const OG_CONTENT_HEIGHT = OG_HEIGHT - OG_HEADER_HEIGHT - OG_FOOTER_HEIGHT;
export const OG_PADDING = 40;

// Colors (from BRAND_GUIDELINES.md)
export const OG_COLORS = {
  // Background gradient (Hero Gradient)
  backgroundStart: '#3b0764', // primary-950
  backgroundMid: '#581c87', // primary-900
  backgroundEnd: '#7e22ce', // primary-700

  // Text colors
  textPrimary: '#ffffff',
  textSecondary: 'rgba(255, 255, 255, 0.9)',
  textMuted: 'rgba(255, 255, 255, 0.7)',

  // Score colors
  scorePositive: '#22c55e', // success-500
  scoreNegative: '#ef4444', // error-500
  scoreNeutral: '#9ca3af', // gray-400

  // Category badge
  badgeBackground: 'rgba(255, 255, 255, 0.15)',
  badgeBorder: 'rgba(255, 255, 255, 0.3)',

  // Accent
  accent: '#a855f7', // primary-500
} as const;

// Typography
export const OG_FONTS = {
  // Title (idea title)
  titleSize: 48,
  titleWeight: 700,
  titleLineHeight: 1.2,

  // Site name in header
  siteNameSize: 24,
  siteNameWeight: 600,

  // Score
  scoreSize: 56,
  scoreWeight: 700,
  scoreLabelSize: 14,

  // Category badge
  badgeSize: 16,
  badgeWeight: 500,

  // Footer/author
  footerSize: 20,
  footerWeight: 400,

  // Header label (Score:)
  labelSize: 14,
  labelWeight: 400,
} as const;

// Text truncation
export const OG_TEXT = {
  maxTitleLength: 80,
  maxTitleLines: 2,
  maxAuthorLength: 30,
} as const;

// Cache settings
export const OG_CACHE = {
  ideaRevalidate: 3600, // 1 hour for idea OG images
  staticRevalidate: false, // Static for default OG image
} as const;

/**
 * Truncate text to max length, adding ellipsis if needed
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 3).trim() + '...';
}

/**
 * Format score with sign
 */
export function formatScore(score: number): string {
  if (score > 0) return `+${score}`;
  return score.toString();
}

/**
 * Get score color based on value
 */
export function getScoreColor(score: number): string {
  if (score > 0) return OG_COLORS.scorePositive;
  if (score < 0) return OG_COLORS.scoreNegative;
  return OG_COLORS.scoreNeutral;
}
