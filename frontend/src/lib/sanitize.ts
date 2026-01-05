import DOMPurify from 'dompurify';

/**
 * Allowed HTML tags for rich text content
 */
const ALLOWED_TAGS = [
  // Text formatting
  'p',
  'br',
  'strong',
  'b',
  'em',
  'i',
  'u',
  's',
  'del',
  // Headings
  'h2',
  'h3',
  // Lists
  'ul',
  'ol',
  'li',
  // Blocks
  'blockquote',
  'pre',
  'code',
  // Note: 'a' (links) are NOT allowed to prevent javascript: protocol XSS
];

/**
 * Allowed attributes for HTML tags
 * Note: href is NOT allowed to prevent javascript: protocol attacks
 * Links are stripped - if links are needed, use a dedicated LinkRenderer component
 */
const ALLOWED_ATTR: string[] = [];

// Note: Links are stripped completely, so no afterSanitizeAttributes hook needed

/**
 * Sanitize HTML content to prevent XSS attacks.
 *
 * @param html - Raw HTML string from editor or database
 * @returns Sanitized HTML safe for rendering
 *
 * @example
 * ```tsx
 * const safeHtml = sanitizeHtml(userContent);
 * return <div dangerouslySetInnerHTML={{ __html: safeHtml }} />;
 * ```
 */
export function sanitizeHtml(html: string): string {
  if (!html) return '';

  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    // Don't allow data: URLs which could be used for XSS
    ALLOW_DATA_ATTR: false,
    // Don't allow javascript: URLs
    FORBID_TAGS: ['script', 'style', 'iframe', 'form', 'input'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover'],
  });
}

/**
 * Check if content is empty (only whitespace, empty tags, or <br>)
 */
export function isContentEmpty(html: string): boolean {
  if (!html) return true;

  // Remove HTML tags and check if anything remains
  const textContent = html
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/g, ' ')
    .trim();

  return textContent.length === 0;
}

/**
 * Get plain text length from HTML (for character counting)
 */
export function getTextLength(html: string): number {
  if (!html) return 0;

  // Create temporary element to extract text
  if (typeof document !== 'undefined') {
    const temp = document.createElement('div');
    temp.innerHTML = html;
    return temp.textContent?.length || 0;
  }

  // Fallback for SSR: strip tags
  return html.replace(/<[^>]*>/g, '').length;
}

/**
 * Convert plain text to HTML paragraphs (for backward compatibility)
 */
export function plainTextToHtml(text: string): string {
  if (!text) return '';

  // If already looks like HTML, return as-is
  if (text.includes('<p>') || text.includes('<br>')) {
    return text;
  }

  // Convert line breaks to paragraphs
  return text
    .split(/\n\n+/)
    .map((para) => `<p>${para.replace(/\n/g, '<br>')}</p>`)
    .join('');
}

/**
 * Extract plain text from HTML for search/comparison purposes
 *
 * @param html - HTML string from editor or database
 * @returns Plain text content without HTML tags
 *
 * @example
 * ```tsx
 * const plainText = htmlToPlainText('<p>Hello <strong>world</strong></p>');
 * // Returns: "Hello world"
 * ```
 */
export function htmlToPlainText(html: string): string {
  if (!html) return '';

  if (typeof document !== 'undefined') {
    const temp = document.createElement('div');
    temp.innerHTML = html;
    return temp.textContent || '';
  }

  // Fallback for SSR
  return html
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .trim();
}
