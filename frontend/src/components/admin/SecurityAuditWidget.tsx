'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { adminAPI } from '@/lib/api';
import type { SecuritySummary, SecurityEventItem } from '@/types';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';

interface SecurityAuditWidgetProps {
  className?: string;
}

export function SecurityAuditWidget({ className = '' }: SecurityAuditWidgetProps) {
  const { t } = useTranslation();

  const [summary, setSummary] = useState<SecuritySummary | null>(null);
  const [events, setEvents] = useState<SecurityEventItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const [summaryData, eventsData] = await Promise.all([
        adminAPI.security.getSummary(),
        adminAPI.security.getEvents({ limit: 10 }),
      ]);
      setSummary(summaryData);
      setEvents(eventsData.events);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('admin.security.loadError'));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const getEventIcon = (eventType: string): string => {
    switch (eventType) {
      case 'LOGIN_SUCCESS':
        return '\u2713'; // checkmark
      case 'LOGIN_FAILED':
        return '\u2717'; // X mark
      case 'LOGOUT':
        return '\u2190'; // left arrow
      case 'PASSWORD_RESET_REQUEST':
      case 'PASSWORD_CHANGED':
        return '\u26BF'; // key symbol
      case 'ACCOUNT_LOCKED':
        return '\u26A0'; // warning
      default:
        return '\u2022'; // bullet
    }
  };

  const getEventColor = (eventType: string): string => {
    switch (eventType) {
      case 'LOGIN_SUCCESS':
        return 'text-green-600 dark:text-green-400';
      case 'LOGIN_FAILED':
        return 'text-red-600 dark:text-red-400';
      case 'LOGOUT':
        return 'text-gray-600 dark:text-gray-400';
      case 'ACCOUNT_LOCKED':
        return 'text-orange-600 dark:text-orange-400';
      default:
        return 'text-blue-600 dark:text-blue-400';
    }
  };

  const getEventLabel = (eventType: string): string => {
    switch (eventType) {
      case 'LOGIN_SUCCESS':
        return t('admin.security.loginSuccess');
      case 'LOGIN_FAILED':
        return t('admin.security.loginFailed');
      case 'LOGOUT':
        return t('admin.security.logout');
      case 'PASSWORD_RESET_REQUEST':
      case 'PASSWORD_CHANGED':
        return t('admin.security.passwordReset');
      case 'ACCOUNT_LOCKED':
        return t('admin.security.accountLocked');
      default:
        return eventType;
    }
  };

  const getFailureReasonLabel = (reason: string | null): string | null => {
    if (!reason) return null;
    switch (reason) {
      case 'invalid_password':
        return t('admin.security.invalidPassword');
      case 'user_not_found':
        return t('admin.security.userNotFound');
      case 'account_inactive':
        return t('admin.security.accountInactive');
      case 'rate_limited':
        return t('admin.security.rateLimited');
      default:
        return reason;
    }
  };

  // Loading skeleton
  if (isLoading && !summary) {
    return (
      <Card className={`p-4 sm:p-5 overflow-hidden ${className}`}>
        <div className="animate-pulse">
          <div className="flex items-center justify-between mb-4">
            <div className="h-5 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-8 w-8 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
          <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="text-center p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
                <div className="h-6 w-12 bg-gray-200 dark:bg-gray-700 rounded mx-auto mb-1" />
                <div className="h-3 w-16 bg-gray-200 dark:bg-gray-700 rounded mx-auto" />
              </div>
            ))}
          </div>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-gray-100 dark:bg-gray-800 rounded" />
            ))}
          </div>
        </div>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className={`p-4 sm:p-5 overflow-hidden ${className}`}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <span role="img" aria-label="lock">
              &#128274;
            </span>
            {t('admin.security.title')}
          </h2>
          <Button
            onClick={loadData}
            variant="secondary"
            className="!px-2 !py-1 text-xs"
            aria-label={t('common.refresh')}
          >
            &#x21bb;
          </Button>
        </div>
        <div className="p-3 rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      </Card>
    );
  }

  // No data state
  if (!summary) {
    return (
      <Card className={`p-4 sm:p-5 overflow-hidden ${className}`}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold flex items-center gap-2">
            <span role="img" aria-label="lock">
              &#128274;
            </span>
            {t('admin.security.title')}
          </h2>
          <Button
            onClick={loadData}
            variant="secondary"
            className="!px-2 !py-1 text-xs"
            aria-label={t('common.refresh')}
          >
            &#x21bb;
          </Button>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{t('admin.security.noEvents')}</p>
      </Card>
    );
  }

  return (
    <Card className={`p-4 sm:p-5 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm sm:text-base font-semibold flex items-center gap-2">
          <span role="img" aria-label="lock">
            &#128274;
          </span>
          {t('admin.security.title')}
        </h2>
        <Button
          onClick={loadData}
          variant="secondary"
          className="!px-2 !py-1 text-xs"
          disabled={isLoading}
          aria-label={t('common.refresh')}
        >
          {isLoading ? '...' : '\u21bb'}
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-4">
        <div className="text-center p-2 sm:p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <div className="text-lg sm:text-xl font-bold text-green-700 dark:text-green-400">
            {summary.successful_logins_24h}
          </div>
          <div className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 leading-tight">
            {t('admin.security.recentLogins')}
          </div>
        </div>
        <div className="text-center p-2 sm:p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
          <div className="text-lg sm:text-xl font-bold text-red-700 dark:text-red-400">
            {summary.failed_attempts_24h}
          </div>
          <div className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 leading-tight">
            {t('admin.security.failedAttempts')}
          </div>
        </div>
        <div className="text-center p-2 sm:p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <div className="text-lg sm:text-xl font-bold text-blue-700 dark:text-blue-400">
            {summary.unique_ips_24h}
          </div>
          <div className="text-[10px] sm:text-xs text-gray-600 dark:text-gray-400 leading-tight">
            {t('admin.security.uniqueIps')}
          </div>
        </div>
      </div>

      {/* Suspicious Activity Warning */}
      {summary.suspicious_ips.length > 0 && (
        <div className="mb-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <div className="flex items-center gap-2 text-yellow-800 dark:text-yellow-300">
            <span role="img" aria-label="warning">
              &#9888;
            </span>
            <span className="text-sm font-medium">
              {t('admin.security.suspiciousActivity', { count: summary.suspicious_ips.length })}
            </span>
          </div>
          <ul className="mt-2 space-y-1">
            {summary.suspicious_ips.slice(0, 3).map((ip, idx) => (
              <li
                key={idx}
                className="text-xs text-yellow-700 dark:text-yellow-400 flex justify-between"
              >
                <span className="font-mono">{ip.ip}</span>
                <span>
                  {ip.failed_count} {t('admin.security.failedAttempts').toLowerCase()}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recent Events */}
      <div>
        <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
          {t('admin.security.recentEvents')}
        </h3>
        {events.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">{t('admin.security.noEvents')}</p>
        ) : (
          <div className="max-h-48 overflow-y-auto space-y-2">
            {events.map((event) => (
              <div
                key={event.id}
                className={`flex items-center justify-between p-2 rounded text-sm ${
                  event.event_type === 'LOGIN_FAILED'
                    ? 'bg-red-50 dark:bg-red-900/10'
                    : 'bg-gray-50 dark:bg-gray-800/50'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className={`font-bold ${getEventColor(event.event_type)}`}>
                    {getEventIcon(event.event_type)}
                  </span>
                  <div className="min-w-0">
                    <div className="truncate font-mono text-xs">
                      {event.email || t('common.deletedUser')}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400 flex gap-2">
                      <span>{getEventLabel(event.event_type)}</span>
                      {event.failure_reason && (
                        <span className="text-red-600 dark:text-red-400">
                          ({getFailureReasonLabel(event.failure_reason)})
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="text-right shrink-0 ml-2">
                  <div className="text-xs font-mono text-gray-500 dark:text-gray-400">
                    {event.ip_address || '-'}
                  </div>
                  <div className="text-xs text-gray-400 dark:text-gray-500">{event.time_ago}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Admin Logins Section */}
      {summary.admin_logins_24h > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
            {t('admin.security.adminLogins')} ({summary.admin_logins_24h})
          </h3>
          <div className="space-y-1">
            {summary.recent_admin_logins.slice(0, 3).map((login, idx) => (
              <div key={idx} className="flex items-center justify-between gap-2 text-xs min-w-0">
                <span className="font-mono truncate min-w-0 flex-1" title={login.email}>
                  {login.email}
                </span>
                <div className="flex gap-2 text-gray-500 dark:text-gray-400 shrink-0">
                  <span className="font-mono hidden sm:inline">{login.ip}</span>
                  <span>{login.time_ago}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
