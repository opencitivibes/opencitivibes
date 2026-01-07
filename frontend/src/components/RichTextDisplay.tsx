'use client';

import { useMemo } from 'react';
import { sanitizeHtml, plainTextToHtml } from '@/lib/sanitize';
import type { RichTextDisplayProps } from '@/types/editor';

/**
 * Component for safely displaying rich text HTML content.
 * Sanitizes HTML to prevent XSS attacks and applies consistent styling.
 *
 * @example
 * ```tsx
 * <RichTextDisplay content={idea.description} />
 * ```
 */
export function RichTextDisplay({ content, className = '' }: RichTextDisplayProps) {
  const safeHtml = useMemo(() => {
    if (!content) return '';

    // Convert plain text to HTML if needed (backward compatibility)
    const htmlContent = plainTextToHtml(content);

    // Sanitize to prevent XSS
    return sanitizeHtml(htmlContent);
  }, [content]);

  if (!safeHtml) {
    return null;
  }

  return (
    <div
      className={`
        rich-text-content
        prose prose-sm max-w-none
        prose-headings:font-bold prose-headings:text-gray-900
        prose-h2:text-xl prose-h2:mt-6 prose-h2:mb-3
        prose-h3:text-lg prose-h3:mt-4 prose-h3:mb-2
        prose-p:text-gray-700 prose-p:leading-relaxed prose-p:mb-3
        prose-a:text-primary-600 prose-a:underline hover:prose-a:text-primary-700
        prose-ul:list-disc prose-ul:pl-6 prose-ul:mb-3
        prose-ol:list-decimal prose-ol:pl-6 prose-ol:mb-3
        prose-li:mb-1
        prose-blockquote:border-l-4 prose-blockquote:border-gray-300 prose-blockquote:pl-4 prose-blockquote:italic prose-blockquote:text-gray-600
        prose-code:bg-gray-100 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm
        prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:p-4 prose-pre:rounded-lg prose-pre:overflow-x-auto
        ${className}
      `}
      // nosemgrep: react-dangerouslysetinnerhtml - content sanitized via DOMPurify in sanitizeHtml()
      dangerouslySetInnerHTML={{ __html: safeHtml }}
    />
  );
}
