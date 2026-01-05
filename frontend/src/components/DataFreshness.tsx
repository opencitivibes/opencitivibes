'use client';

import { useTranslation } from 'react-i18next';
import { formatDistanceToNow } from 'date-fns';
import { getDateFnsLocale } from '@/lib/i18n-helpers';
import { Clock, RefreshCw } from 'lucide-react';

interface DataFreshnessProps {
  lastUpdated: Date | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
  className?: string;
}

export function DataFreshness({
  lastUpdated,
  onRefresh,
  isRefreshing = false,
  className = '',
}: DataFreshnessProps) {
  const { t, i18n } = useTranslation();

  const locale = getDateFnsLocale(i18n.language);

  const timeAgo = lastUpdated
    ? formatDistanceToNow(lastUpdated, { addSuffix: true, locale })
    : null;

  return (
    <div
      className={`flex items-center gap-2 text-xs text-gray-500
                     dark:text-gray-400 ${className}`}
    >
      <Clock className="w-3.5 h-3.5" aria-hidden="true" />
      <span>
        {timeAgo ? t('analytics.lastUpdated', { time: timeAgo }) : t('analytics.loading')}
      </span>

      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded
                     transition-colors disabled:opacity-50"
          aria-label={t('common.refresh')}
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`}
            aria-hidden="true"
          />
        </button>
      )}
    </div>
  );
}
