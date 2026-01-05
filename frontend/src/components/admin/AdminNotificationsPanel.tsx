'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { formatDistanceToNow } from 'date-fns';
import { getDateFnsLocale } from '@/lib/i18n-helpers';
import {
  Bell,
  AlertTriangle,
  MessageSquare,
  ClipboardList,
  UserCheck,
  Flag,
  AlertOctagon,
  RefreshCw,
  ExternalLink,
} from 'lucide-react';
import type { LucideProps } from 'lucide-react';
import { adminAPI } from '@/lib/api';
import type { AdminNotification } from '@/types';

// Polling interval in milliseconds
const POLL_INTERVAL = 60000; // 60 seconds

// Priority styling
const PRIORITY_STYLES: Record<string, { bg: string; border: string; text: string }> = {
  max: {
    bg: 'bg-error-50 dark:bg-error-900/20',
    border: 'border-error-300 dark:border-error-700',
    text: 'text-error-700 dark:text-error-300',
  },
  high: {
    bg: 'bg-warning-50 dark:bg-warning-900/20',
    border: 'border-warning-300 dark:border-warning-700',
    text: 'text-warning-700 dark:text-warning-300',
  },
  default: {
    bg: 'bg-white dark:bg-gray-800',
    border: 'border-gray-200 dark:border-gray-700',
    text: 'text-gray-700 dark:text-gray-300',
  },
  low: {
    bg: 'bg-gray-50 dark:bg-gray-800',
    border: 'border-gray-200 dark:border-gray-700',
    text: 'text-gray-500 dark:text-gray-400',
  },
  min: {
    bg: 'bg-gray-50 dark:bg-gray-800',
    border: 'border-gray-100 dark:border-gray-700',
    text: 'text-gray-400 dark:text-gray-500',
  },
};

// Topic icon component that uses conditional rendering
function TopicIcon({ topic, ...props }: { topic: string } & LucideProps) {
  const suffix = topic.split('-').pop() || '';

  switch (suffix) {
    case 'ideas':
      return <ClipboardList {...props} />;
    case 'comments':
      return <MessageSquare {...props} />;
    case 'appeals':
      return <AlertTriangle {...props} />;
    case 'officials':
      return <UserCheck {...props} />;
    case 'reports':
      return <Flag {...props} />;
    case 'critical':
      return <AlertOctagon {...props} />;
    default:
      return <Bell {...props} />;
  }
}

interface NotificationItemProps {
  notification: AdminNotification;
  language: string;
}

const DEFAULT_STYLE = {
  bg: 'bg-white dark:bg-gray-800',
  border: 'border-gray-200 dark:border-gray-700',
  text: 'text-gray-700 dark:text-gray-300',
};

function NotificationItem({ notification, language }: NotificationItemProps) {
  const { t } = useTranslation();
  const styles = PRIORITY_STYLES[notification.priority] ?? DEFAULT_STYLE;
  const locale = getDateFnsLocale(language);

  const timeAgo = formatDistanceToNow(new Date(notification.timestamp), {
    addSuffix: true,
    locale,
  });

  return (
    <div
      className={`p-4 rounded-lg border ${styles.bg} ${styles.border} transition-colors hover:shadow-sm`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-full ${styles.bg} ${styles.text}`}>
          <TopicIcon topic={notification.topic} className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className={`text-xs font-medium ${styles.text}`}>
              {notification.topic_display}
            </span>
            <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
              {timeAgo}
            </span>
          </div>
          <h4 className="font-medium text-gray-900 dark:text-gray-100 mt-1">
            {notification.title}
          </h4>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 whitespace-pre-wrap">
            {notification.message}
          </p>
          {notification.click_url && (
            <a
              href={notification.click_url}
              className="inline-flex items-center gap-1 text-sm text-primary-600 dark:text-primary-400 hover:text-primary-800 dark:hover:text-primary-300 mt-2"
            >
              <ExternalLink className="w-3 h-3" />
              {t('admin.notifications.viewDetails', 'View details')}
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AdminNotificationsPanel() {
  const { t, i18n } = useTranslation();
  const [notifications, setNotifications] = useState<AdminNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const language = i18n.language?.substring(0, 2) === 'fr' ? 'fr' : 'en';

  const fetchNotifications = useCallback(async () => {
    try {
      setError(null);
      const data = await adminAPI.notifications.getRecent({
        since: '24h',
        limit: 100,
        language,
      });
      setNotifications(data);
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
      setError(t('admin.notifications.fetchError', 'Failed to fetch notifications'));
    } finally {
      setLoading(false);
    }
  }, [language, t]);

  // Initial fetch and polling
  useEffect(() => {
    fetchNotifications();

    const interval = setInterval(fetchNotifications, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const handleRefresh = () => {
    setLoading(true);
    fetchNotifications();
  };

  // Group notifications by priority for summary
  const priorityCounts = notifications.reduce(
    (acc, n) => {
      acc[n.priority] = (acc[n.priority] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            {t('admin.notifications.title', 'System Notifications')}
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {t('admin.notifications.subtitle', 'Recent notifications from the last 24 hours')}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          {t('admin.notifications.refresh', 'Refresh')}
        </button>
      </div>

      {/* Summary badges */}
      {notifications.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {priorityCounts.max && priorityCounts.max > 0 && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-error-100 dark:bg-error-900/30 text-error-800 dark:text-error-300">
              {priorityCounts.max} {t('admin.notifications.critical', 'critical')}
            </span>
          )}
          {priorityCounts.high && priorityCounts.high > 0 && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-warning-100 dark:bg-warning-900/30 text-warning-800 dark:text-warning-300">
              {priorityCounts.high} {t('admin.notifications.highPriority', 'high priority')}
            </span>
          )}
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300">
            {notifications.length} {t('admin.notifications.total', 'total')}
          </span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="p-4 rounded-lg bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-700 text-error-700 dark:text-error-300">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading && notifications.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      )}

      {/* Empty state */}
      {!loading && notifications.length === 0 && !error && (
        <div className="text-center py-12">
          <Bell className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <p className="text-gray-500 dark:text-gray-400">
            {t('admin.notifications.empty', 'No notifications in the last 24 hours')}
          </p>
        </div>
      )}

      {/* Notification list */}
      {notifications.length > 0 && (
        <div className="space-y-3">
          {notifications.map((notification) => (
            <NotificationItem
              key={notification.id}
              notification={notification}
              language={language}
            />
          ))}
        </div>
      )}

      {/* Last refresh timestamp */}
      {lastRefresh && (
        <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
          {t('admin.notifications.lastRefresh', 'Last refreshed')}{' '}
          {formatDistanceToNow(lastRefresh, {
            addSuffix: true,
            locale: getDateFnsLocale(language),
          })}
        </p>
      )}
    </div>
  );
}
