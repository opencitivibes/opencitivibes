'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { useToast } from '@/hooks/useToast';
import { analyticsAPI } from '@/lib/api';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { AnomaliesTable } from '@/components/analytics/AnomaliesTable';
import {
  RefreshCw,
  Scale,
  AlertTriangle,
  CheckCircle,
  TrendingDown,
  ChevronLeft,
} from 'lucide-react';
import type { ScoreAnomaliesResponse } from '@/types';

const THRESHOLD_OPTIONS = [10, 20, 30, 50] as const;

interface SummaryCardProps {
  title: string;
  value: number;
  icon: React.ReactNode;
  colorClass: string;
}

function SummaryCard({ title, value, icon, colorClass }: SummaryCardProps) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</span>
        <div className={colorClass}>{icon}</div>
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        {value.toLocaleString()}
      </div>
    </Card>
  );
}

function SummaryCardSkeleton() {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        <div className="h-5 w-5 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      </div>
      <div className="h-8 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
    </Card>
  );
}

export default function WeightedScoresDashboardPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { error: showError, success: showSuccess } = useToast();

  // Data state
  const [data, setData] = useState<ScoreAnomaliesResponse | null>(null);
  const [threshold, setThreshold] = useState<number>(20);

  // UI state
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Compute summary counts
  const summaryStats = {
    totalAnalyzed: data?.count ?? 0,
    lowDivergence: data?.anomalies.filter((a) => Math.abs(a.divergence_percent) < 10).length ?? 0,
    mediumDivergence:
      data?.anomalies.filter(
        (a) => Math.abs(a.divergence_percent) >= 10 && Math.abs(a.divergence_percent) < 30
      ).length ?? 0,
    highDivergence: data?.anomalies.filter((a) => Math.abs(a.divergence_percent) >= 30).length ?? 0,
  };

  // Fetch data
  const fetchData = useCallback(
    async (showLoadingState = true) => {
      if (showLoadingState) {
        setIsLoading(true);
      }
      setError(null);

      try {
        const response = await analyticsAPI.getScoreAnomalies(threshold / 100);
        setData(response);
      } catch (err) {
        console.error('Failed to fetch weighted scores:', err);
        setError(t('analytics.error'));
        showError(t('analytics.error'), { isRaw: true });
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [threshold, t, showError]
  );

  // Auth check and initial fetch
  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

    if (!token) {
      router.push('/');
      return;
    }

    if (!user) {
      return;
    }

    if (!user.is_global_admin) {
      router.push('/');
      return;
    }

    fetchData();
  }, [user, router, fetchData]);

  // Handle threshold change
  const handleThresholdChange = (newThreshold: number) => {
    setThreshold(newThreshold);
  };

  // Refetch when threshold changes
  useEffect(() => {
    if (user?.is_global_admin && !isLoading) {
      fetchData(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threshold]);

  // Handle refresh
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await analyticsAPI.refreshCache('weighted_scores');
      await fetchData(false);
      showSuccess(t('common.refresh'), { isRaw: true });
    } catch (err) {
      console.error('Failed to refresh:', err);
      showError(t('analytics.error'), { isRaw: true });
    }
  };

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      {/* Breadcrumb */}
      <nav className="mb-4" aria-label={t('common.breadcrumb')}>
        <ol className="flex items-center gap-2 text-sm">
          <li>
            <Link
              href="/admin"
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
            >
              {t('nav.admin')}
            </Link>
          </li>
          <li className="text-gray-400 dark:text-gray-500">/</li>
          <li>
            <Link
              href="/admin/analytics"
              className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
            >
              {t('nav.analytics')}
            </Link>
          </li>
          <li className="text-gray-400 dark:text-gray-500">/</li>
          <li className="text-gray-900 dark:text-gray-100 font-medium">
            {t('analytics.weightedScores.title')}
          </li>
        </ol>
      </nav>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <PageHeader title={t('analytics.weightedScores.title')} />
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {t('analytics.weightedScores.description')}
          </p>
        </div>
        <Link
          href="/admin/analytics"
          className="inline-flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100"
        >
          <ChevronLeft className="h-4 w-4" />
          {t('common.back')}
        </Link>
      </div>

      {error && (
        <div className="mb-6">
          <Alert variant="error" dismissible onDismiss={() => setError(null)}>
            {error}
          </Alert>
        </div>
      )}

      {/* Controls */}
      <Card className="mb-6 p-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          {/* Threshold selector */}
          <div className="flex items-center gap-3">
            <label
              htmlFor="threshold-select"
              className="text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              {t('analytics.weightedScores.threshold')}:
            </label>
            <select
              id="threshold-select"
              value={threshold}
              onChange={(e) => handleThresholdChange(Number(e.target.value))}
              className="px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
            >
              {THRESHOLD_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}%
                </option>
              ))}
            </select>
          </div>

          {/* Refresh button */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </button>
        </div>
      </Card>

      {/* Summary Cards */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {t('analytics.overview')}
        </h2>
        {isLoading ? (
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <SummaryCardSkeleton key={i} />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
            <SummaryCard
              title={t('analytics.weightedScores.totalAnalyzed')}
              value={summaryStats.totalAnalyzed}
              icon={<Scale className="h-5 w-5" />}
              colorClass="text-blue-500"
            />
            <SummaryCard
              title={t('analytics.weightedScores.lowDivergence')}
              value={summaryStats.lowDivergence}
              icon={<CheckCircle className="h-5 w-5" />}
              colorClass="text-green-500"
            />
            <SummaryCard
              title={t('analytics.weightedScores.mediumDivergence')}
              value={summaryStats.mediumDivergence}
              icon={<TrendingDown className="h-5 w-5" />}
              colorClass="text-yellow-500"
            />
            <SummaryCard
              title={t('analytics.weightedScores.highDivergence')}
              value={summaryStats.highDivergence}
              icon={<AlertTriangle className="h-5 w-5" />}
              colorClass="text-red-500"
            />
          </div>
        )}
      </section>

      {/* Anomalies Table */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {t('analytics.weightedScores.anomaliesTitle')}
        </h2>
        <AnomaliesTable anomalies={data?.anomalies ?? []} isLoading={isLoading} />
      </section>
    </PageContainer>
  );
}
