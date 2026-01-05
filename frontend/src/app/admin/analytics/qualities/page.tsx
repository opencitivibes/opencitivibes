'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { useToast } from '@/hooks/useToast';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { getIntlLocaleCode } from '@/lib/i18n-helpers';
import { analyticsAPI } from '@/lib/api';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { Button } from '@/components/Button';
import {
  ArrowLeft,
  TrendingUp,
  Heart,
  ExternalLink,
  Sun,
  AlertTriangle,
  Handshake,
  Leaf,
  Users,
  TreeDeciduous,
  Baby,
} from 'lucide-react';
import type { QualityAnalyticsResponse, QualityDistribution } from '@/types';

// Render icon based on icon name from API
function QualityIcon({ iconName, className }: { iconName: string | null; className?: string }) {
  switch (iconName) {
    case 'heart':
      return <Heart className={className} />;
    case 'sun':
      return <Sun className={className} />;
    case 'alert-triangle':
      return <AlertTriangle className={className} />;
    case 'hand-helping':
      return <Handshake className={className} />;
    case 'leaf':
      return <Leaf className={className} />;
    case 'users':
      return <Users className={className} />;
    case 'tree':
      return <TreeDeciduous className={className} />;
    case 'baby':
      return <Baby className={className} />;
    default:
      return <Heart className={className} />;
  }
}

// Get Tailwind color class based on API color
function getColorClasses(color: string | null) {
  const colorMap: Record<string, { bg: string; bgDark: string; text: string }> = {
    rose: {
      bg: 'bg-rose-100',
      bgDark: 'dark:bg-rose-900/30',
      text: 'text-rose-500',
    },
    amber: {
      bg: 'bg-amber-100',
      bgDark: 'dark:bg-amber-900/30',
      text: 'text-amber-500',
    },
    red: {
      bg: 'bg-red-100',
      bgDark: 'dark:bg-red-900/30',
      text: 'text-red-500',
    },
    emerald: {
      bg: 'bg-emerald-100',
      bgDark: 'dark:bg-emerald-900/30',
      text: 'text-emerald-500',
    },
    blue: {
      bg: 'bg-blue-100',
      bgDark: 'dark:bg-blue-900/30',
      text: 'text-blue-500',
    },
    green: {
      bg: 'bg-green-100',
      bgDark: 'dark:bg-green-900/30',
      text: 'text-green-500',
    },
    purple: {
      bg: 'bg-purple-100',
      bgDark: 'dark:bg-purple-900/30',
      text: 'text-purple-500',
    },
  };

  return (
    colorMap[color || 'gray'] || {
      bg: 'bg-gray-100',
      bgDark: 'dark:bg-gray-900/30',
      text: 'text-gray-500',
    }
  );
}

function QualityCard({
  quality,
}: {
  quality: {
    quality_key: string;
    quality_name_en: string;
    quality_name_fr: string;
    quality_name_es?: string;
    icon: string | null;
    color: string | null;
    ideas: Array<{ id: number; title: string; count: number }>;
  };
}) {
  const { getQualityName } = useLocalizedField();
  const colors = getColorClasses(quality.color);
  const name = getQualityName(quality);

  return (
    <Card>
      <div className="flex items-center gap-3 mb-4">
        <div className={`p-2 rounded-lg ${colors.bg} ${colors.bgDark}`}>
          <QualityIcon iconName={quality.icon} className={`w-5 h-5 ${colors.text}`} />
        </div>
        <h3 className="font-semibold text-gray-900 dark:text-gray-100">{name}</h3>
      </div>
      <ul className="space-y-3">
        {quality.ideas.map((idea, index) => (
          <li key={idea.id} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-400 w-6">#{index + 1}</span>
              <Link
                href={`/ideas/${idea.id}`}
                className="text-sm text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 hover:underline line-clamp-1"
              >
                {idea.title}
              </Link>
            </div>
            <span className={`text-sm font-semibold ${colors.text}`}>{idea.count}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}

function QualityDistributionBar({
  item,
  maxCount,
}: {
  item: QualityDistribution;
  maxCount: number;
}) {
  const { getQualityName } = useLocalizedField();
  const colors = getColorClasses(item.color);
  const percentage = maxCount > 0 ? (item.count / maxCount) * 100 : 0;
  const name = getQualityName(item);

  return (
    <div className="flex items-center gap-4">
      <div className={`p-2 rounded-lg ${colors.bg} ${colors.bgDark}`}>
        <QualityIcon iconName={item.icon} className={`w-5 h-5 ${colors.text}`} />
      </div>
      <div className="flex-1">
        <div className="flex items-center justify-between mb-1">
          <span className="font-medium text-gray-900 dark:text-gray-100">{name}</span>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {item.count} ({item.percentage.toFixed(1)}%)
          </span>
        </div>
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full ${colors.text.replace('text-', 'bg-')} rounded-full transition-all duration-500`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  );
}

export default function QualityAnalyticsPage() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { error: showError } = useToast();

  const [data, setData] = useState<QualityAnalyticsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

    if (!token) {
      router.push('/');
      return;
    }

    if (!user) return;

    if (!user.is_global_admin) {
      router.push('/');
      return;
    }

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await analyticsAPI.getQualityAnalytics();
        setData(response);
      } catch (err) {
        console.error('Failed to fetch quality analytics:', err);
        setError(t('analytics.error'));
        showError(t('analytics.error'), { isRaw: true });
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [user, router, t, showError]);

  if (!user || !user.is_global_admin) {
    return null;
  }

  const maxCount = data?.distribution.reduce((max, item) => Math.max(max, item.count), 0) || 0;

  return (
    <PageContainer maxWidth="6xl" paddingY="normal">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <Button variant="ghost" size="sm" onClick={() => router.push('/admin/analytics')}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t('common.back')}
        </Button>
        <Link
          href="/officials"
          className="flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
        >
          <ExternalLink className="w-4 h-4" />
          {t('analytics.viewOfficialsDashboard')}
        </Link>
      </div>

      <div className="mb-6">
        <PageHeader title={t('analytics.qualityAnalytics.title', 'Quality Voting Analytics')} />
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          {t(
            'analytics.qualityAnalytics.subtitle',
            'Insights into how citizens are using quality feedback on votes'
          )}
        </p>
      </div>

      {error && (
        <div className="mb-6">
          <Alert variant="error" dismissible onDismiss={() => setError(null)}>
            {error}
          </Alert>
        </div>
      )}

      {isLoading ? (
        <div className="grid gap-6 md:grid-cols-3 mb-8">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded" />
            </Card>
          ))}
        </div>
      ) : data ? (
        <>
          {/* Summary Cards */}
          <div className="grid gap-6 md:grid-cols-3 mb-8">
            {/* Total Upvotes */}
            <Card>
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-primary-100 dark:bg-primary-900/30">
                  <TrendingUp className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t('analytics.qualityAnalytics.totalUpvotes', 'Total Upvotes')}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {data.total_upvotes.toLocaleString()}
                  </p>
                </div>
              </div>
            </Card>

            {/* Votes with Qualities */}
            <Card>
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-emerald-100 dark:bg-emerald-900/30">
                  <Heart className="w-6 h-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t('analytics.qualityAnalytics.votesWithQualities', 'Votes with Qualities')}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {data.votes_with_qualities.toLocaleString()}
                  </p>
                </div>
              </div>
            </Card>

            {/* Adoption Rate */}
            <Card>
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-amber-100 dark:bg-amber-900/30">
                  <TrendingUp className="w-6 h-6 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {t('analytics.qualityAnalytics.adoptionRate', 'Adoption Rate')}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {data.adoption_rate}%
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Quality Distribution */}
          <Card className="mb-8">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-6">
              {t('analytics.qualityAnalytics.distribution', 'Quality Distribution')}
            </h2>
            <div className="space-y-6">
              {data.distribution.length > 0 ? (
                data.distribution.map((item) => (
                  <QualityDistributionBar key={item.quality_key} item={item} maxCount={maxCount} />
                ))
              ) : (
                <p className="text-center text-gray-500 dark:text-gray-400 py-8">
                  {t('analytics.qualityAnalytics.noData', 'No quality data yet')}
                </p>
              )}
            </div>
          </Card>

          {/* Top Ideas by Quality */}
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            {t('analytics.qualityAnalytics.topIdeas', 'Top Ideas by Quality')}
          </h2>
          <div className="grid gap-6 md:grid-cols-2">
            {data.top_ideas_by_quality.map((quality) => (
              <QualityCard key={quality.quality_key} quality={quality} />
            ))}
          </div>

          {/* Last Updated */}
          {data.generated_at && (
            <p className="mt-8 text-sm text-gray-500 dark:text-gray-400 text-right">
              {t('analytics.lastUpdated', {
                time: new Date(data.generated_at).toLocaleString(getIntlLocaleCode(i18n.language)),
              })}
            </p>
          )}
        </>
      ) : null}
    </PageContainer>
  );
}
