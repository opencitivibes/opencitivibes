'use client';

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield } from 'lucide-react';
import type { TrustDistribution } from '@/types';

interface TrustBadgeProps {
  trustDistribution?: TrustDistribution;
  size?: 'sm' | 'md';
  loading?: boolean;
}

export function TrustBadge({ trustDistribution, size = 'sm', loading = false }: TrustBadgeProps) {
  const { t } = useTranslation();

  const { trustPercent, colorClasses, bgClasses } = useMemo(() => {
    if (!trustDistribution || trustDistribution.total_votes === 0) {
      return { trustPercent: 0, colorClasses: '', bgClasses: '' };
    }

    const { excellent, good, total_votes } = trustDistribution;
    const percent = Math.round(((excellent + good) / total_votes) * 100);

    let color: string;
    let bg: string;
    if (percent >= 70) {
      color = 'text-emerald-600 dark:text-emerald-400';
      bg = 'bg-emerald-100 dark:bg-emerald-900/50';
    } else if (percent >= 50) {
      color = 'text-amber-600 dark:text-amber-400';
      bg = 'bg-amber-100 dark:bg-amber-900/50';
    } else {
      color = 'text-red-600 dark:text-red-400';
      bg = 'bg-red-100 dark:bg-red-900/50';
    }

    return { trustPercent: percent, colorClasses: color, bgClasses: bg };
  }, [trustDistribution]);

  const tooltipContent = useMemo(() => {
    if (!trustDistribution || trustDistribution.total_votes === 0) return '';

    const { excellent, good, average, below_average, low, total_votes } = trustDistribution;
    const getPercent = (count: number) => Math.round((count / total_votes) * 100);

    return [
      `${t('quality.trust.excellent')}: ${getPercent(excellent)}%`,
      `${t('quality.trust.good')}: ${getPercent(good)}%`,
      `${t('quality.trust.average')}: ${getPercent(average)}%`,
      `${t('quality.trust.below_average')}: ${getPercent(below_average)}%`,
      `${t('quality.trust.low')}: ${getPercent(low)}%`,
    ].join('\n');
  }, [trustDistribution, t]);

  // Loading skeleton
  if (loading) {
    const sizeClasses = size === 'sm' ? 'w-12 h-5' : 'w-16 h-6';
    return (
      <div
        className={`${sizeClasses} rounded-full bg-gray-200 dark:bg-gray-700 animate-pulse`}
        aria-hidden="true"
      />
    );
  }

  // Don't render if no data
  if (!trustDistribution || trustDistribution.total_votes === 0) {
    return null;
  }

  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5 gap-1' : 'text-sm px-2.5 py-1 gap-1.5';
  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';

  return (
    <div
      className={`inline-flex items-center rounded-full ${bgClasses} ${colorClasses} ${sizeClasses} font-medium ring-2 ring-white dark:ring-gray-800`}
      title={tooltipContent}
      aria-label={t('quality.trust.badge_label', { percent: trustPercent })}
      role="img"
    >
      <Shield className={iconSize} aria-hidden="true" />
      <span>{trustPercent}%</span>
    </div>
  );
}
