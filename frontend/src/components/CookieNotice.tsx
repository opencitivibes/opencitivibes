'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Cookie, Shield } from 'lucide-react';
import { Button } from '@/components/Button';
import Link from 'next/link';

const STORAGE_KEY = 'cookie_notice_acknowledged';
const DATE_KEY = 'cookie_notice_date';

export function CookieNotice() {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Check if user has already acknowledged
    const acknowledged = localStorage.getItem(STORAGE_KEY);
    if (!acknowledged) {
      // Delay showing to avoid flash on page load
      const timer = setTimeout(() => setVisible(true), 1000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAcknowledge = () => {
    localStorage.setItem(STORAGE_KEY, 'true');
    localStorage.setItem(DATE_KEY, new Date().toISOString());
    setVisible(false);
  };

  const handleDismiss = () => {
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-labelledby="cookie-notice-title"
      aria-describedby="cookie-notice-description"
      className="fixed bottom-0 left-0 right-0 z-[60] p-4 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 shadow-lg"
    >
      <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-start sm:items-center gap-4">
        <div className="flex items-start gap-3 flex-1">
          <Cookie className="w-6 h-6 text-amber-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <h2 id="cookie-notice-title" className="sr-only">
              {t('cookies.title', 'Cookie Notice')}
            </h2>
            <p id="cookie-notice-description" className="text-sm text-gray-700 dark:text-gray-300">
              {t('cookies.notice')}
            </p>
            <Link
              href="/privacy#cookies"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded"
            >
              {t('cookies.learnMore')}
            </Link>
          </div>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Button
            onClick={handleAcknowledge}
            size="sm"
            className="flex items-center gap-2 flex-1 sm:flex-none justify-center"
          >
            <Shield className="w-4 h-4" aria-hidden="true" />
            {t('cookies.acknowledge')}
          </Button>
          <button
            onClick={handleDismiss}
            aria-label={t('common.close')}
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}
