'use client';

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Link from 'next/link';
import DOMPurify from 'dompurify';
import { legalAPI } from '@/lib/api';

interface LegalDocument {
  version: string;
  last_updated: string;
  html_content: string;
}

interface LegalPageContentProps {
  documentType: 'terms' | 'privacy';
  title: string;
}

export default function LegalPageContent({ documentType, title }: LegalPageContentProps) {
  const { t, i18n } = useTranslation();
  const [document, setDocument] = useState<LegalDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchLegalContent() {
      try {
        setLoading(true);
        setError(null);
        const data = await legalAPI.getDocument(documentType, i18n.language);
        setDocument(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    fetchLegalContent();
  }, [documentType, i18n.language]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-md p-8 md:p-12">
            <div className="animate-pulse">
              <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-24 mb-6" />
              <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3 mb-8" />
              <div className="space-y-4">
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full" />
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6" />
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-4/5" />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-md p-8 md:p-12 text-center">
            <p className="text-red-500 dark:text-red-400">{error || t('errors.loadFailed')}</p>
            <Link
              href="/"
              className="mt-4 inline-flex items-center text-primary-600 hover:text-primary-700 transition-colors"
            >
              {t('common.backToHome')}
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-12">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-md p-8 md:p-12">
          <Link
            href="/"
            className="inline-flex items-center text-primary-600 hover:text-primary-700 mb-6 transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            {t('common.backToHome')}
          </Link>

          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-8">{title}</h1>

            <div
              className="legal-content mt-6"
              dangerouslySetInnerHTML={{
                __html: DOMPurify.sanitize(document.html_content, {
                  ALLOWED_TAGS: [
                    'p',
                    'br',
                    'strong',
                    'em',
                    'u',
                    'b',
                    'i',
                    'h1',
                    'h2',
                    'h3',
                    'h4',
                    'h5',
                    'h6',
                    'ul',
                    'ol',
                    'li',
                    'a',
                    'table',
                    'thead',
                    'tbody',
                    'tr',
                    'th',
                    'td',
                    'blockquote',
                    'hr',
                    'span',
                    'div',
                  ],
                  ALLOWED_ATTR: ['href', 'class', 'target', 'rel'],
                  FORBID_TAGS: ['script', 'style', 'iframe', 'form', 'input', 'object', 'embed'],
                  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
                }),
              }}
            />
          </div>

          <div className="mt-12 pt-8 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-500 dark:text-gray-400">
            <p>
              {document.last_updated && t('legal.lastUpdated', { date: document.last_updated })}
              {document.last_updated && document.version && ' | '}
              {document.version && t('legal.version', { version: document.version })}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
