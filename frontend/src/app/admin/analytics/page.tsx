'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { useToast } from '@/hooks/useToast';
import { getIntlLocaleCode } from '@/lib/i18n-helpers';
import { analyticsAPI } from '@/lib/api';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { OverviewCards } from '@/components/analytics/OverviewCards';
import { DateRangeSelector } from '@/components/analytics/DateRangeSelector';
import { ActivityChart } from '@/components/analytics/ActivityChart';
import { CategoryPieChart } from '@/components/analytics/CategoryPieChart';
import { TopContributorsTable } from '@/components/analytics/TopContributorsTable';
import { ExportButton } from '@/components/analytics/ExportButton';
import type {
  OverviewMetrics,
  TrendsResponse,
  CategoriesAnalyticsResponse,
  DateRange,
  Granularity,
} from '@/types';

export default function AnalyticsDashboardPage() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { error: showError } = useToast();

  // Data state
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [trends, setTrends] = useState<TrendsResponse | null>(null);
  const [categories, setCategories] = useState<CategoriesAnalyticsResponse | null>(null);

  // UI state
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter state
  const [dateRange, setDateRange] = useState<DateRange>(() => {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - 30);
    return { startDate, endDate };
  });
  const [granularity, setGranularity] = useState<Granularity>('week');

  // Format date for API
  const formatDate = (date: Date): string => {
    return date.toISOString().split('T')[0] ?? '';
  };

  // Fetch data
  const fetchData = useCallback(
    async (showLoadingState = true) => {
      if (showLoadingState) {
        setIsLoading(true);
      }
      setError(null);

      try {
        // Fetch all data in parallel
        const [overviewData, trendsData, categoriesData] = await Promise.all([
          analyticsAPI.getOverview(),
          analyticsAPI.getTrends({
            start_date: formatDate(dateRange.startDate),
            end_date: formatDate(dateRange.endDate),
            granularity,
          }),
          analyticsAPI.getCategoriesAnalytics(),
        ]);

        setOverview(overviewData);
        setTrends(trendsData);
        setCategories(categoriesData);
      } catch (err) {
        console.error('Failed to fetch analytics:', err);
        setError(t('analytics.error'));
        showError(t('analytics.error'), { isRaw: true });
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [dateRange, granularity, t, showError]
  );

  // Auth check and initial fetch
  useEffect(() => {
    // Check if there's a token - if so, user might still be loading
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

    // If no token, definitely not authenticated - redirect
    if (!token) {
      router.push('/');
      return;
    }

    // If we have a token but no user yet, wait for user to load
    if (!user) {
      return;
    }

    // User loaded but not admin - redirect
    if (!user.is_global_admin) {
      router.push('/');
      return;
    }

    // User is admin - fetch data
    fetchData();
  }, [user, router, fetchData]);

  // Handle date range change
  const handleDateRangeChange = (newRange: DateRange) => {
    setDateRange(newRange);
  };

  // Handle granularity change
  const handleGranularityChange = (newGranularity: Granularity) => {
    setGranularity(newGranularity);
  };

  // Handle refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await analyticsAPI.refreshCache();
      await fetchData(false);
    } catch (err) {
      console.error('Failed to refresh:', err);
      showError(t('analytics.error'), { isRaw: true });
    }
  };

  // Refetch when filters change
  useEffect(() => {
    if (user?.is_global_admin && !isLoading) {
      fetchData(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateRange, granularity]);

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <PageHeader title={t('analytics.title')} />
        <ExportButton dateRange={dateRange} />
      </div>

      {error && (
        <div className="mb-6">
          <Alert variant="error" dismissible onDismiss={() => setError(null)}>
            {error}
          </Alert>
        </div>
      )}

      {/* Date Range and Filters */}
      <Card className="mb-6">
        <DateRangeSelector
          dateRange={dateRange}
          granularity={granularity}
          onDateRangeChange={handleDateRangeChange}
          onGranularityChange={handleGranularityChange}
          onRefresh={handleRefresh}
          isRefreshing={isRefreshing}
        />
      </Card>

      {/* Overview Cards */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {t('analytics.overview')}
        </h2>
        <OverviewCards data={overview} isLoading={isLoading} />
      </section>

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2 mb-8">
        {/* Trends Chart */}
        <ActivityChart data={trends} isLoading={isLoading} />

        {/* Category Distribution */}
        <CategoryPieChart data={categories} isLoading={isLoading} />
      </div>

      {/* Top Contributors */}
      <section className="mb-8">
        <TopContributorsTable />
      </section>

      {/* Last Updated */}
      {overview && (
        <p className="text-sm text-gray-500 dark:text-gray-400 text-right">
          {t('analytics.lastUpdated', {
            time: new Date(overview.generated_at).toLocaleString(getIntlLocaleCode(i18n.language)),
          })}
        </p>
      )}
    </PageContainer>
  );
}
