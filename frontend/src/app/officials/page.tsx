'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { officialsAPI } from '@/lib/api';
import type {
  OfficialsQualityOverview,
  OfficialsTopIdeaByQuality,
  OfficialsCategoryQualityBreakdown,
  OfficialsTimeSeriesPoint,
} from '@/types';
import {
  Download,
  TrendingUp,
  Users,
  Target,
  Heart,
  Info,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Cell,
} from 'recharts';
import Link from 'next/link';

const QUALITY_COLORS: Record<string, string> = {
  community_benefit: '#f43f5e', // rose
  quality_of_life: '#f59e0b', // amber
  urgent: '#ef4444', // red
  would_volunteer: '#10b981', // emerald
  eco_friendly: '#22c55e', // green
  family_friendly: '#8b5cf6', // violet
};

export default function OfficialsDashboard() {
  const { t } = useTranslation();
  const { isDark } = useTheme();
  const { getField, getCategoryName } = useLocalizedField();
  const [overview, setOverview] = useState<OfficialsQualityOverview | null>(null);
  const [topIdeas, setTopIdeas] = useState<OfficialsTopIdeaByQuality[]>([]);
  const [categories, setCategories] = useState<OfficialsCategoryQualityBreakdown[]>([]);
  const [trends, setTrends] = useState<OfficialsTimeSeriesPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(false);
  const [mounted, setMounted] = useState(false);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(false);
    try {
      const [overviewRes, topIdeasRes, categoriesRes, trendsRes] = await Promise.all([
        officialsAPI.getOverview(),
        officialsAPI.getTopIdeas(undefined, 5),
        officialsAPI.getCategoryBreakdown(),
        officialsAPI.getTrends(30),
      ]);

      setOverview(overviewRes);
      setTopIdeas(topIdeasRes);
      setCategories(categoriesRes);
      setTrends(trendsRes);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
      setError(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExport = () => {
    officialsAPI.exportAnalyticsCSV();
  };

  if (isLoading || !mounted) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  if (error || !overview) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          {t('errors.loadFailed')}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          {t('officials.tryAgainLater')}
        </p>
        <button
          onClick={fetchData}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          {t('officials.refreshData')}
        </button>
      </div>
    );
  }

  const getName = (item: { name_en: string; name_fr: string; name_es?: string }) =>
    getField(item, 'name');

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header with export */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
          {t('officials.qualityAnalytics')}
        </h2>
        <button
          onClick={handleExport}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors w-full sm:w-auto"
        >
          <Download className="w-4 h-4" />
          {t('officials.exportCSV')}
        </button>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm group relative">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {t('officials.totalUpvotes')}
                </p>
                <div className="relative group/info">
                  <Info className="w-3.5 h-3.5 text-gray-400 cursor-help" />
                  <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all z-50 pointer-events-none">
                    {t('officials.totalUpvotesTooltip')}
                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-gray-900 dark:border-t-gray-700" />
                  </div>
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {overview.total_upvotes.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm group relative">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-100 dark:bg-emerald-900/30 rounded-lg">
              <Target className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {t('officials.votesWithQualities')}
                </p>
                <div className="relative group/info">
                  <Info className="w-3.5 h-3.5 text-gray-400 cursor-help" />
                  <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all z-50 pointer-events-none">
                    {t('officials.votesWithQualitiesTooltip')}
                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-gray-900 dark:border-t-gray-700" />
                  </div>
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {overview.votes_with_qualities.toLocaleString()}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm group relative">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <Users className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {t('officials.adoptionRate')}
                </p>
                <div className="relative group/info">
                  <Info className="w-3.5 h-3.5 text-gray-400 cursor-help" />
                  <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-56 p-2 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all z-50 pointer-events-none">
                    {t('officials.adoptionRateTooltip')}
                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-gray-900 dark:border-t-gray-700" />
                  </div>
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {(overview.adoption_rate * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm group relative">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-rose-100 dark:bg-rose-900/30 rounded-lg">
              <Heart className="w-5 h-5 text-rose-600 dark:text-rose-400" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-1">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {t('officials.qualityTypes')}
                </p>
                <div className="relative group/info">
                  <Info className="w-3.5 h-3.5 text-gray-400 cursor-help" />
                  <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-48 p-2 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg opacity-0 invisible group-hover/info:opacity-100 group-hover/info:visible transition-all z-50 pointer-events-none">
                    {t('officials.qualityTypesTooltip')}
                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-gray-900 dark:border-t-gray-700" />
                  </div>
                </div>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {overview.quality_distribution.length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quality Distribution */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            {t('officials.qualityDistribution')}
          </h3>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={overview.quality_distribution} margin={{ bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#374151' : '#e5e7eb'} />
              <XAxis
                dataKey="key"
                tickFormatter={(key) => t(`qualities.${key}`, { defaultValue: key })}
                tick={{ fontSize: 11, fill: isDark ? '#9ca3af' : '#6b7280' }}
                angle={-30}
                textAnchor="end"
                interval={0}
                height={70}
              />
              <YAxis tick={{ fill: isDark ? '#9ca3af' : '#6b7280' }} />
              <Tooltip
                labelFormatter={(key) => t(`qualities.${key}`, { defaultValue: key })}
                formatter={(value) => [value, t('analytics.count')]}
                contentStyle={{
                  backgroundColor: isDark ? '#1f2937' : '#fff',
                  borderColor: isDark ? '#374151' : '#e5e7eb',
                }}
                labelStyle={{ color: isDark ? '#f3f4f6' : '#111827', fontWeight: 500 }}
                itemStyle={{ color: isDark ? '#f3f4f6' : '#111827' }}
                cursor={{ fill: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }}
              />
              <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]}>
                {overview.quality_distribution.map((entry) => (
                  <Cell key={entry.key} fill={QUALITY_COLORS[entry.key] || '#6366f1'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Trends Over Time */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            {t('officials.trends30Days')}
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#374151' : '#e5e7eb'} />
              <XAxis dataKey="date" tick={{ fontSize: 12, fill: isDark ? '#9ca3af' : '#6b7280' }} />
              <YAxis tick={{ fill: isDark ? '#9ca3af' : '#6b7280' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: isDark ? '#1f2937' : '#fff',
                  borderColor: isDark ? '#374151' : '#e5e7eb',
                  color: isDark ? '#f3f4f6' : '#111827',
                }}
                labelStyle={{ color: isDark ? '#f3f4f6' : '#111827' }}
                itemStyle={{ color: isDark ? '#f3f4f6' : '#111827' }}
              />
              <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Ideas */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {t('officials.topIdeas')}
            </h3>
            <Link
              href="/officials/ideas"
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              {t('common.loadMore')}
            </Link>
          </div>
          <ul className="space-y-3">
            {topIdeas.map((idea, index) => (
              <li
                key={idea.idea_id}
                className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <span className="w-6 h-6 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded-full text-sm font-medium">
                    {index + 1}
                  </span>
                  <div>
                    <Link
                      href={`/officials/ideas/${idea.idea_id}`}
                      className="text-sm font-medium text-gray-900 dark:text-white hover:text-primary-600"
                    >
                      {idea.title}
                    </Link>
                    <p className="text-xs text-gray-500">{getCategoryName(idea)}</p>
                  </div>
                </div>
                <span className="text-sm font-semibold text-primary-600">{idea.quality_count}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Category Breakdown */}
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            {t('officials.categoryBreakdown')}
          </h3>
          <ul className="space-y-3">
            {categories.slice(0, 5).map((cat) => (
              <li
                key={cat.category_id}
                className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0"
              >
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {getName(cat)}
                  </p>
                  <p className="text-xs text-gray-500">
                    {cat.idea_count} {t('officials.ideas')}
                  </p>
                </div>
                <span className="text-sm font-semibold text-primary-600">
                  {cat.quality_count} {t('officials.qualities')}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
