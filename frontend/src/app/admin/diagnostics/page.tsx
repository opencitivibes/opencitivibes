'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { captureException, captureMessage, isSentryEnabled } from '@/lib/sentry-utils';
import { useAuthStore } from '@/store/authStore';
import { adminAPI } from '@/lib/api';
import type { DatabaseDiagnosticsResponse, SystemResourcesResponse } from '@/types';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';

interface DiagnosticStatus {
  status: 'idle' | 'loading' | 'success' | 'error';
  message: string;
}

export default function DiagnosticsPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);

  // Status states for each test
  const [sentryStatus, setSentryStatus] = useState<DiagnosticStatus>({
    status: 'idle',
    message: '',
  });
  const [ntfyStatus, setNtfyStatus] = useState<DiagnosticStatus>({
    status: 'idle',
    message: '',
  });
  const [apiStatus, setApiStatus] = useState<DiagnosticStatus>({
    status: 'idle',
    message: '',
  });
  const [smtpStatus, setSmtpStatus] = useState<DiagnosticStatus>({
    status: 'idle',
    message: '',
  });
  const [smtpInfo, setSmtpInfo] = useState<{
    provider: string;
    host: string | null;
    port: number | null;
    details: string | null;
  } | null>(null);
  const [platformInfo, setPlatformInfo] = useState<{
    platform: string;
    version: string;
  } | null>(null);
  const [dbStatus, setDbStatus] = useState<DiagnosticStatus>({
    status: 'idle',
    message: '',
  });
  const [dbInfo, setDbInfo] = useState<DatabaseDiagnosticsResponse | null>(null);
  const [systemStatus, setSystemStatus] = useState<DiagnosticStatus>({
    status: 'idle',
    message: '',
  });
  const [systemInfo, setSystemInfo] = useState<SystemResourcesResponse | null>(null);
  // Initialize browser info lazily on client side
  const getBrowserInfo = () => {
    if (typeof window === 'undefined') return null;
    return {
      userAgent: navigator.userAgent,
      language: navigator.language,
      cookiesEnabled: navigator.cookieEnabled,
      online: navigator.onLine,
    };
  };

  const [browserInfo] = useState(getBrowserInfo);

  // Redirect non-admin users
  useEffect(() => {
    if (user && !user.is_global_admin) {
      router.push('/');
    }
  }, [user, router]);

  if (!user?.is_global_admin) {
    return null;
  }

  // Sentry tests
  const triggerError = () => {
    throw new Error('Test Sentry Error from Admin Diagnostics');
  };

  const captureManually = () => {
    setSentryStatus({ status: 'loading', message: '' });
    if (!isSentryEnabled) {
      setSentryStatus({
        status: 'error',
        message: 'Sentry is not configured (no DSN)',
      });
      return;
    }
    try {
      captureException(new Error('Manual Sentry Test - Admin Diagnostics'));
      setSentryStatus({
        status: 'success',
        message: t('admin.diagnostics.errorCaptured'),
      });
    } catch {
      setSentryStatus({
        status: 'error',
        message: 'Failed to capture error',
      });
    }
  };

  const sendTestMessage = () => {
    setSentryStatus({ status: 'loading', message: '' });
    if (!isSentryEnabled) {
      setSentryStatus({
        status: 'error',
        message: 'Sentry is not configured (no DSN)',
      });
      return;
    }
    try {
      captureMessage('Test message from Admin Diagnostics', 'info');
      setSentryStatus({
        status: 'success',
        message: t('admin.diagnostics.messageSent'),
      });
    } catch {
      setSentryStatus({
        status: 'error',
        message: 'Failed to send message',
      });
    }
  };

  // ntfy test
  const testNtfy = async () => {
    setNtfyStatus({ status: 'loading', message: t('admin.diagnostics.sending') });
    try {
      const result = await adminAPI.notifications.sendTest();
      setNtfyStatus({
        status: result.success ? 'success' : 'error',
        message: result.message,
      });
    } catch (error) {
      setNtfyStatus({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to send test notification',
      });
    }
  };

  // SMTP test
  const testSmtp = async () => {
    setSmtpStatus({ status: 'loading', message: t('admin.diagnostics.testing') });
    setSmtpInfo(null);
    try {
      const result = await adminAPI.diagnostics.testSmtp();
      setSmtpInfo({
        provider: result.provider,
        host: result.host,
        port: result.port,
        details: result.details,
      });
      setSmtpStatus({
        status: result.success ? 'success' : 'error',
        message: result.message,
      });
    } catch (error) {
      setSmtpStatus({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to test SMTP connection',
      });
    }
  };

  // API health check
  const checkApiHealth = async () => {
    setApiStatus({ status: 'loading', message: t('admin.diagnostics.checking') });
    try {
      const [health, info] = await Promise.all([
        adminAPI.diagnostics.checkHealth(),
        adminAPI.diagnostics.getPlatformInfo(),
      ]);
      setPlatformInfo(info);
      setApiStatus({
        status: health.status === 'healthy' ? 'success' : 'error',
        message: `API Status: ${health.status}`,
      });
    } catch (error) {
      setApiStatus({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to connect to API',
      });
    }
  };

  // Database check
  const checkDatabase = async () => {
    setDbStatus({ status: 'loading', message: t('admin.diagnostics.checking') });
    setDbInfo(null);
    try {
      const result = await adminAPI.diagnostics.checkDatabase();
      setDbInfo(result);
      setDbStatus({
        status: result.connected ? 'success' : 'error',
        message: result.connected
          ? t('admin.diagnostics.dbConnected')
          : result.error || t('admin.diagnostics.dbDisconnected'),
      });
    } catch (error) {
      setDbStatus({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to check database',
      });
    }
  };

  // System resources check
  const checkSystemResources = async () => {
    setSystemStatus({ status: 'loading', message: t('admin.diagnostics.checking') });
    setSystemInfo(null);
    try {
      const result = await adminAPI.diagnostics.getSystemResources();
      setSystemInfo(result);
      setSystemStatus({
        status: result.error ? 'error' : 'success',
        message: result.error || t('admin.diagnostics.systemResourcesLoaded'),
      });
    } catch (error) {
      setSystemStatus({
        status: 'error',
        message: error instanceof Error ? error.message : 'Failed to check system resources',
      });
    }
  };

  // Format uptime as human-readable string
  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h ${mins}m`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  // Get color for disk/memory usage percentage
  const getUsageColor = (percent: number): string => {
    if (percent >= 90) return 'text-red-600 dark:text-red-400';
    if (percent >= 75) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
  };

  const getStatusColor = (status: DiagnosticStatus['status']) => {
    switch (status) {
      case 'success':
        return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200';
      case 'error':
        return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200';
      case 'loading':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200';
      default:
        return 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <PageContainer>
      <PageHeader
        title={t('admin.diagnostics.title')}
        description={t('admin.diagnostics.description')}
      />

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left: System Resources Vertical Column */}
        <div className="lg:w-64 space-y-4">
          {/* System Resources Quick Check */}
          <Card className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold">{t('admin.diagnostics.systemResources')}</h2>
              <Button
                onClick={checkSystemResources}
                variant="secondary"
                className="!px-2 !py-1 text-xs"
                disabled={systemStatus.status === 'loading'}
              >
                {systemStatus.status === 'loading' ? '...' : '↻'}
              </Button>
            </div>

            {systemStatus.status === 'idle' && (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {t('admin.diagnostics.clickToLoad')}
              </p>
            )}

            {systemStatus.status === 'loading' && (
              <p className="text-xs text-gray-500 dark:text-gray-400 animate-pulse">
                {t('admin.diagnostics.checking')}
              </p>
            )}

            {systemStatus.status === 'error' && (
              <div className="p-2 rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 text-xs">
                {systemStatus.message}
              </div>
            )}

            {systemInfo && (
              <div className="space-y-4">
                {/* Disk Usage */}
                {systemInfo.disk && (
                  <div>
                    <div className="flex justify-between items-baseline mb-1">
                      <span className="text-xs text-gray-600 dark:text-gray-400">
                        {t('admin.diagnostics.diskUsage')}
                      </span>
                      <span
                        className={`text-sm font-bold ${getUsageColor(systemInfo.disk.used_percent)}`}
                      >
                        {systemInfo.disk.used_percent}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full ${
                          systemInfo.disk.used_percent >= 90
                            ? 'bg-red-500'
                            : systemInfo.disk.used_percent >= 75
                              ? 'bg-yellow-500'
                              : 'bg-green-500'
                        }`}
                        style={{ width: `${systemInfo.disk.used_percent}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                      <span>{systemInfo.disk.free_gb} GB free</span>
                      <span>{systemInfo.disk.total_gb} GB</span>
                    </div>
                  </div>
                )}

                {/* Memory Usage */}
                {systemInfo.memory_used_percent !== null && (
                  <div>
                    <div className="flex justify-between items-baseline mb-1">
                      <span className="text-xs text-gray-600 dark:text-gray-400">
                        {t('admin.diagnostics.memoryUsage')}
                      </span>
                      <span
                        className={`text-sm font-bold ${getUsageColor(systemInfo.memory_used_percent)}`}
                      >
                        {systemInfo.memory_used_percent}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full ${
                          systemInfo.memory_used_percent >= 90
                            ? 'bg-red-500'
                            : systemInfo.memory_used_percent >= 75
                              ? 'bg-yellow-500'
                              : 'bg-green-500'
                        }`}
                        style={{ width: `${systemInfo.memory_used_percent}%` }}
                      />
                    </div>
                    {systemInfo.load_average && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        Load: {systemInfo.load_average.join(' / ')}
                      </div>
                    )}
                  </div>
                )}

                {/* Uptime */}
                {systemInfo.uptime_seconds !== null && (
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.diagnostics.uptime')}
                    </span>
                    <span className="font-mono">{formatUptime(systemInfo.uptime_seconds)}</span>
                  </div>
                )}

                {/* Database Size */}
                {systemInfo.database_size && (
                  <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
                    <div className="flex justify-between items-baseline mb-1">
                      <span className="text-xs text-gray-600 dark:text-gray-400">
                        {t('admin.diagnostics.databaseSize')}
                      </span>
                      <span className="text-sm font-bold text-blue-600 dark:text-blue-400">
                        {systemInfo.database_size.size_mb.toFixed(1)} MB
                      </span>
                    </div>
                    <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                      <span className="uppercase">{systemInfo.database_size.database_type}</span>
                      {systemInfo.database_size.file_path && (
                        <span
                          className="font-mono truncate max-w-[100px]"
                          title={systemInfo.database_size.file_path}
                        >
                          {systemInfo.database_size.file_path}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </Card>
        </div>

        {/* Middle: Test Panels */}
        <div className="flex-1 grid gap-6 sm:grid-cols-2">
          {/* Sentry Tests */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-2">{t('admin.diagnostics.sentryTests')}</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {t('admin.diagnostics.sentryDescription')}
            </p>

            <div className="space-y-3">
              <Button onClick={captureManually} variant="primary" className="w-full">
                {t('admin.diagnostics.captureError')}
              </Button>

              <Button onClick={sendTestMessage} variant="secondary" className="w-full">
                {t('admin.diagnostics.sendMessage')}
              </Button>

              <Button
                onClick={triggerError}
                variant="secondary"
                className="w-full !bg-red-600 !text-white hover:!bg-red-700 dark:!bg-red-700 dark:hover:!bg-red-800"
              >
                {t('admin.diagnostics.triggerCrash')}
              </Button>
            </div>

            {sentryStatus.message && (
              <div className={`mt-4 p-3 rounded-lg text-sm ${getStatusColor(sentryStatus.status)}`}>
                {sentryStatus.message}
              </div>
            )}

            <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
              {t('admin.diagnostics.checkDashboard')}
            </p>
          </Card>

          {/* ntfy Tests */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-2">{t('admin.diagnostics.ntfyTests')}</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {t('admin.diagnostics.ntfyDescription')}
            </p>

            <div className="space-y-3">
              <Button
                onClick={testNtfy}
                variant="primary"
                className="w-full"
                disabled={ntfyStatus.status === 'loading'}
              >
                {ntfyStatus.status === 'loading'
                  ? t('admin.diagnostics.sending')
                  : t('admin.diagnostics.sendTestNotification')}
              </Button>
            </div>

            {ntfyStatus.message && (
              <div className={`mt-4 p-3 rounded-lg text-sm ${getStatusColor(ntfyStatus.status)}`}>
                {ntfyStatus.message}
              </div>
            )}

            <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
              {t('admin.diagnostics.ntfyNote')}
            </p>
          </Card>

          {/* SMTP Test */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-2">{t('admin.diagnostics.smtpTests')}</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {t('admin.diagnostics.smtpDescription')}
            </p>

            <div className="space-y-3">
              <Button
                onClick={testSmtp}
                variant="primary"
                className="w-full"
                disabled={smtpStatus.status === 'loading'}
              >
                {smtpStatus.status === 'loading'
                  ? t('admin.diagnostics.testing')
                  : t('admin.diagnostics.testSmtp')}
              </Button>
            </div>

            {smtpStatus.message && (
              <div className={`mt-4 p-3 rounded-lg text-sm ${getStatusColor(smtpStatus.status)}`}>
                {smtpStatus.message}
              </div>
            )}

            {smtpInfo && (
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between gap-2">
                  <dt className="text-gray-600 dark:text-gray-400 shrink-0">
                    {t('admin.diagnostics.provider')}
                  </dt>
                  <dd className="font-mono text-right">{smtpInfo.provider}</dd>
                </div>
                {smtpInfo.host && (
                  <div className="flex justify-between gap-2">
                    <dt className="text-gray-600 dark:text-gray-400 shrink-0">
                      {t('admin.diagnostics.host')}
                    </dt>
                    <dd className="font-mono text-right">
                      {smtpInfo.host}:{smtpInfo.port}
                    </dd>
                  </div>
                )}
                {smtpInfo.details && (
                  <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                    <dd className="font-mono text-xs text-gray-500 dark:text-gray-400">
                      {smtpInfo.details}
                    </dd>
                  </div>
                )}
              </dl>
            )}

            <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
              {t('admin.diagnostics.smtpNote')}
            </p>
          </Card>

          {/* API Health Check */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-2">{t('admin.diagnostics.apiHealth')}</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {t('admin.diagnostics.apiDescription')}
            </p>

            <div className="space-y-3">
              <Button
                onClick={checkApiHealth}
                variant="primary"
                className="w-full"
                disabled={apiStatus.status === 'loading'}
              >
                {apiStatus.status === 'loading'
                  ? t('admin.diagnostics.checking')
                  : t('admin.diagnostics.checkApi')}
              </Button>
            </div>

            {apiStatus.message && (
              <div className={`mt-4 p-3 rounded-lg text-sm ${getStatusColor(apiStatus.status)}`}>
                {apiStatus.message}
              </div>
            )}

            {platformInfo && (
              <dl className="mt-4 space-y-1 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-600 dark:text-gray-400">Platform</dt>
                  <dd className="font-mono">{platformInfo.platform}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600 dark:text-gray-400">Version</dt>
                  <dd className="font-mono">{platformInfo.version}</dd>
                </div>
              </dl>
            )}
          </Card>

          {/* Database Check */}
          <Card className="p-6">
            <h2 className="text-lg font-semibold mb-2">{t('admin.diagnostics.dbTests')}</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {t('admin.diagnostics.dbDescription')}
            </p>

            <div className="space-y-3">
              <Button
                onClick={checkDatabase}
                variant="primary"
                className="w-full"
                disabled={dbStatus.status === 'loading'}
              >
                {dbStatus.status === 'loading'
                  ? t('admin.diagnostics.checking')
                  : t('admin.diagnostics.checkDb')}
              </Button>
            </div>

            {dbStatus.message && (
              <div className={`mt-4 p-3 rounded-lg text-sm ${getStatusColor(dbStatus.status)}`}>
                {dbStatus.message}
              </div>
            )}

            {dbInfo && (
              <div className="mt-4 space-y-3">
                {/* Database type badge */}
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${
                      dbInfo.database_type === 'postgresql'
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                        : dbInfo.database_type === 'sqlite'
                          ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
                    }`}
                  >
                    {dbInfo.database_type === 'postgresql' && '🐘 '}
                    {dbInfo.database_type === 'sqlite' && '📄 '}
                    {dbInfo.database_type.toUpperCase()}
                  </span>
                  {dbInfo.connected && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300">
                      ● Connected
                    </span>
                  )}
                </div>

                <dl className="space-y-2 text-sm">
                  <div className="flex justify-between gap-2">
                    <dt className="text-gray-600 dark:text-gray-400 shrink-0">
                      {t('admin.diagnostics.dbUrl')}
                    </dt>
                    <dd
                      className="font-mono text-xs text-right truncate max-w-[180px]"
                      title={dbInfo.database_url_masked}
                    >
                      {dbInfo.database_url_masked}
                    </dd>
                  </div>
                </dl>

                {/* Pool info for PostgreSQL */}
                {dbInfo.pool_info && (
                  <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                    <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                      {t('admin.diagnostics.poolInfo')}
                    </h3>
                    <dl className="space-y-1 text-xs">
                      <div className="flex justify-between">
                        <dt className="text-gray-600 dark:text-gray-400">
                          {t('admin.diagnostics.poolSize')}
                        </dt>
                        <dd className="font-mono">{dbInfo.pool_info.pool_size ?? 'N/A'}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-600 dark:text-gray-400">
                          {t('admin.diagnostics.checkedIn')}
                        </dt>
                        <dd className="font-mono">{dbInfo.pool_info.checked_in}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-600 dark:text-gray-400">
                          {t('admin.diagnostics.checkedOut')}
                        </dt>
                        <dd className="font-mono">{dbInfo.pool_info.checked_out}</dd>
                      </div>
                      <div className="flex justify-between">
                        <dt className="text-gray-600 dark:text-gray-400">
                          {t('admin.diagnostics.overflow')}
                        </dt>
                        <dd className="font-mono">{dbInfo.pool_info.overflow}</dd>
                      </div>
                    </dl>
                  </div>
                )}

                {/* Tables section */}
                {dbInfo.tables.length > 0 && (
                  <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                    <h3 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                      {t('admin.diagnostics.tables')} ({dbInfo.tables.length})
                    </h3>
                    <div className="max-h-40 overflow-y-auto">
                      <table className="w-full text-xs">
                        <thead className="sticky top-0 bg-white dark:bg-gray-800">
                          <tr className="text-left text-gray-500 dark:text-gray-400">
                            <th className="pb-1">{t('admin.diagnostics.tableName')}</th>
                            <th className="pb-1 text-right">{t('admin.diagnostics.rows')}</th>
                          </tr>
                        </thead>
                        <tbody className="font-mono">
                          {dbInfo.tables.map((table) => (
                            <tr
                              key={table.name}
                              className="border-t border-gray-100 dark:border-gray-700"
                            >
                              <td className="py-1">{table.name}</td>
                              <td className="py-1 text-right">
                                {table.row_count?.toLocaleString() ?? '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
              {t('admin.diagnostics.dbNote')}
            </p>
          </Card>
        </div>

        {/* Right: Info Widgets Sidebar */}
        <div className="lg:w-80 space-y-6">
          {/* Current Session */}
          <Card className="p-5">
            <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              {t('admin.diagnostics.sessionInfo')}
            </h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-600 dark:text-gray-400">User ID</dt>
                <dd className="font-mono">{user?.id}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600 dark:text-gray-400">Email</dt>
                <dd className="font-mono text-xs truncate max-w-[150px]" title={user?.email}>
                  {user?.email}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600 dark:text-gray-400">Global Admin</dt>
                <dd className="font-mono">{user?.is_global_admin ? '✓ Yes' : '✗ No'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600 dark:text-gray-400">Official</dt>
                <dd className="font-mono">{user?.is_official ? '✓ Yes' : '✗ No'}</dd>
              </div>
            </dl>
          </Card>

          {/* System Info */}
          <Card className="p-5">
            <h2 className="text-base font-semibold mb-3">{t('admin.diagnostics.systemInfo')}</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-600 dark:text-gray-400">Environment</dt>
                <dd className="font-mono">{process.env.NODE_ENV}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600 dark:text-gray-400">Sentry DSN</dt>
                <dd className="font-mono text-xs">
                  {process.env.NEXT_PUBLIC_SENTRY_DSN ? '✓ Configured' : '✗ Not set'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600 dark:text-gray-400">Release</dt>
                <dd className="font-mono">{process.env.NEXT_PUBLIC_SENTRY_RELEASE || 'unknown'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-600 dark:text-gray-400">Instance</dt>
                <dd className="font-mono">{process.env.NEXT_PUBLIC_INSTANCE_NAME || 'default'}</dd>
              </div>
            </dl>
          </Card>

          {/* Browser Info */}
          <Card className="p-5">
            <h2 className="text-base font-semibold mb-3">{t('admin.diagnostics.browserInfo')}</h2>
            {browserInfo ? (
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-600 dark:text-gray-400">Language</dt>
                  <dd className="font-mono">{browserInfo.language}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600 dark:text-gray-400">Cookies</dt>
                  <dd className="font-mono">
                    {browserInfo.cookiesEnabled ? '✓ Enabled' : '✗ Disabled'}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-gray-600 dark:text-gray-400">Online</dt>
                  <dd className="font-mono">{browserInfo.online ? '✓ Yes' : '✗ No'}</dd>
                </div>
                <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                  <dt className="text-gray-600 dark:text-gray-400 text-xs mb-1">User Agent</dt>
                  <dd
                    className="font-mono text-xs text-gray-500 dark:text-gray-400 break-all"
                    title={browserInfo.userAgent}
                  >
                    {browserInfo.userAgent.slice(0, 80)}...
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="text-sm text-gray-500">Loading...</p>
            )}
          </Card>
        </div>
      </div>
    </PageContainer>
  );
}
