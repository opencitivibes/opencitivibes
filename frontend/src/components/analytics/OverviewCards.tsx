'use client';

import { useTranslation } from 'react-i18next';
import { Card } from '@/components/Card';
import {
  Users,
  Lightbulb,
  ThumbsUp,
  MessageSquare,
  CheckCircle,
  Clock,
  XCircle,
  TrendingUp,
} from 'lucide-react';
import type { OverviewMetrics } from '@/types';

interface OverviewCardsProps {
  data: OverviewMetrics | null;
  isLoading: boolean;
}

interface MetricCardProps {
  title: string;
  value: number;
  subtitle?: string;
  subtitleValue?: number;
  icon: React.ReactNode;
  colorClass?: string;
}

function MetricCardSkeleton() {
  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
        <div className="h-5 w-5 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
      </div>
      <div className="h-8 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-1" />
      <div className="h-3 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
    </Card>
  );
}

function MetricCard({ title, value, subtitle, subtitleValue, icon, colorClass }: MetricCardProps) {
  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</span>
        <div className={`${colorClass || 'text-gray-400 dark:text-gray-500'}`}>{icon}</div>
      </div>
      <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        {value.toLocaleString()}
      </div>
      {subtitle && subtitleValue !== undefined && (
        <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 mt-1">
          <TrendingUp className="h-3 w-3 text-green-500" />
          <span>
            +{subtitleValue} {subtitle}
          </span>
        </p>
      )}
    </Card>
  );
}

export function OverviewCards({ data, isLoading }: OverviewCardsProps) {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(8)].map((_, i) => (
          <MetricCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        title={t('analytics.totalUsers')}
        value={data.total_users}
        subtitle={t('analytics.thisWeek').toLowerCase()}
        subtitleValue={data.users_this_week}
        icon={<Users className="h-5 w-5" />}
        colorClass="text-blue-500"
      />
      <MetricCard
        title={t('analytics.totalIdeas')}
        value={data.total_ideas}
        subtitle={t('analytics.thisWeek').toLowerCase()}
        subtitleValue={data.ideas_this_week}
        icon={<Lightbulb className="h-5 w-5" />}
        colorClass="text-yellow-500"
      />
      <MetricCard
        title={t('analytics.totalVotes')}
        value={data.total_votes}
        subtitle={t('analytics.thisWeek').toLowerCase()}
        subtitleValue={data.votes_this_week}
        icon={<ThumbsUp className="h-5 w-5" />}
        colorClass="text-green-500"
      />
      <MetricCard
        title={t('analytics.totalComments')}
        value={data.total_comments}
        subtitle={t('analytics.thisWeek').toLowerCase()}
        subtitleValue={data.comments_this_week}
        icon={<MessageSquare className="h-5 w-5" />}
        colorClass="text-purple-500"
      />
      <MetricCard
        title={t('analytics.approvedIdeas')}
        value={data.approved_ideas}
        icon={<CheckCircle className="h-5 w-5" />}
        colorClass="text-green-500"
      />
      <MetricCard
        title={t('analytics.pendingIdeas')}
        value={data.pending_ideas}
        icon={<Clock className="h-5 w-5" />}
        colorClass="text-yellow-500"
      />
      <MetricCard
        title={t('analytics.rejectedIdeas')}
        value={data.rejected_ideas}
        icon={<XCircle className="h-5 w-5" />}
        colorClass="text-red-500"
      />
      <MetricCard
        title={t('analytics.activeUsers')}
        value={data.active_users}
        icon={<Users className="h-5 w-5" />}
        colorClass="text-blue-500"
      />
    </div>
  );
}
