'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { Flag, Clock, TrendingUp, AlertTriangle, Users, Loader2 } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { adminModerationAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { Badge } from '@/components/Badge';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import type { ModerationStats, FlagReason } from '@/types/moderation';
import { FLAG_REASON_LABELS, PENALTY_TYPE_LABELS, getLocalizedLabel } from '@/types/moderation';

const COLORS = ['#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6'];

export default function ModerationStatsPage() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { error: toastError } = useToast();

  const [stats, setStats] = useState<ModerationStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
      return;
    }

    const loadStats = async () => {
      try {
        const data = await adminModerationAPI.getStats();
        setStats(data);
      } catch (err) {
        console.error('Failed to load moderation stats:', err);
        toastError(t('toast.error'), { isRaw: true });
      } finally {
        setIsLoading(false);
      }
    };

    loadStats();
  }, [user, router, t, toastError]);

  if (!user || !user.is_global_admin) {
    return null;
  }

  if (isLoading) {
    return (
      <PageContainer maxWidth="7xl" paddingY="normal">
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      </PageContainer>
    );
  }

  if (!stats) {
    return (
      <PageContainer maxWidth="7xl" paddingY="normal">
        <div className="text-center py-12">
          <p className="text-gray-500">{t('toast.error')}</p>
        </div>
      </PageContainer>
    );
  }

  const reasonChartData = Object.entries(stats.flags_by_reason).map(([reason, count], index) => ({
    name: getLocalizedLabel(FLAG_REASON_LABELS[reason as FlagReason], i18n.language),
    value: count,
    color: COLORS[index % COLORS.length],
  }));

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <PageHeader title={t('adminModeration.stats.title')} />
      <p className="text-gray-500 mb-6">{t('adminModeration.stats.description')}</p>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('adminModeration.stats.totalFlags')}
            </CardTitle>
            <Flag className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_flags}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('adminModeration.stats.pendingFlags')}
            </CardTitle>
            <Clock className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-error-600">{stats.pending_flags}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('adminModeration.stats.resolvedToday')}
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success-600">{stats.resolved_today}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {t('adminModeration.stats.activePenalties')}
            </CardTitle>
            <AlertTriangle className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.active_penalties}</div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {stats.pending_appeals} {t('adminModeration.stats.pendingAppeals')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2 mb-6">
        {/* Flags Over Time */}
        <Card>
          <CardHeader>
            <CardTitle>{t('adminModeration.stats.flagsOverTime')}</CardTitle>
            <CardDescription>{t('adminModeration.stats.last30Days')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {stats.flags_by_day.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={stats.flags_by_day}>
                    <XAxis
                      dataKey="date"
                      tickFormatter={(date) => new Date(date).toLocaleDateString()}
                      fontSize={12}
                    />
                    <YAxis fontSize={12} />
                    <Tooltip
                      labelFormatter={(date) => new Date(date).toLocaleDateString()}
                      contentStyle={{ backgroundColor: 'white', borderRadius: '8px' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#ef4444"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  {t('analytics.noData')}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Flags by Reason */}
        <Card>
          <CardHeader>
            <CardTitle>{t('adminModeration.stats.flagsByReason')}</CardTitle>
            <CardDescription>{t('adminModeration.stats.pendingOnly')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[320px] sm:h-[300px]">
              {reasonChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={reasonChartData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="45%"
                      outerRadius={60}
                      labelLine={false}
                    >
                      {reasonChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend
                      layout="horizontal"
                      verticalAlign="bottom"
                      align="center"
                      wrapperStyle={{
                        fontSize: '10px',
                        paddingTop: '10px',
                        overflow: 'auto',
                        maxHeight: '100px',
                      }}
                      formatter={(value) => {
                        const item = reasonChartData.find((d) => d.name === value);
                        return `${value} (${item?.value || 0})`;
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  {t('analytics.noData')}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Flagged Users */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            {t('adminModeration.stats.topFlaggedUsers')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {stats.top_flagged_users.length > 0 ? (
            <div className="space-y-4">
              {stats.top_flagged_users.map((flaggedUser) => (
                <div
                  key={flaggedUser.user_id}
                  className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-4 last:border-0"
                >
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">
                      @{flaggedUser.username}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {t('adminModeration.trustScore')}: {flaggedUser.trust_score}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="error">
                      {flaggedUser.pending_flags_count} {t('adminModeration.pending')}
                    </Badge>
                    {flaggedUser.has_active_penalty && flaggedUser.active_penalty_type && (
                      <Badge variant="warning">
                        {getLocalizedLabel(
                          PENALTY_TYPE_LABELS[flaggedUser.active_penalty_type],
                          i18n.language
                        )}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-gray-500 py-8">
              {t('adminModeration.stats.noFlaggedUsers')}
            </p>
          )}
        </CardContent>
      </Card>
    </PageContainer>
  );
}
