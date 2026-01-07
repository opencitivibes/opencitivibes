'use client';

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import type { TrustDistribution } from '@/types';

interface TrustBreakdownProps {
  trustDistribution: TrustDistribution;
}

interface TrustLevel {
  key: keyof Omit<TrustDistribution, 'total_votes'>;
  labelKey: string;
  barClass: string;
  textClass: string;
}

const TRUST_LEVELS: TrustLevel[] = [
  {
    key: 'excellent',
    labelKey: 'quality.trust.excellent',
    barClass: 'bg-emerald-500',
    textClass: 'text-emerald-600 dark:text-emerald-400',
  },
  {
    key: 'good',
    labelKey: 'quality.trust.good',
    barClass: 'bg-green-500',
    textClass: 'text-green-600 dark:text-green-400',
  },
  {
    key: 'average',
    labelKey: 'quality.trust.average',
    barClass: 'bg-amber-500',
    textClass: 'text-amber-600 dark:text-amber-400',
  },
  {
    key: 'below_average',
    labelKey: 'quality.trust.below_average',
    barClass: 'bg-orange-500',
    textClass: 'text-orange-600 dark:text-orange-400',
  },
  {
    key: 'low',
    labelKey: 'quality.trust.low',
    barClass: 'bg-red-500',
    textClass: 'text-red-600 dark:text-red-400',
  },
];

export function TrustBreakdown({ trustDistribution }: TrustBreakdownProps) {
  const { t } = useTranslation();

  const { totalVotes, levels } = useMemo(() => {
    const total = trustDistribution.total_votes;
    if (total === 0) {
      return { totalVotes: 0, levels: [] };
    }

    const levelsWithPercent = TRUST_LEVELS.map((level) => {
      const count = trustDistribution[level.key];
      const percent = Math.round((count / total) * 100);
      return { ...level, count, percent };
    }).filter((level) => level.count > 0);

    return { totalVotes: total, levels: levelsWithPercent };
  }, [trustDistribution]);

  if (totalVotes === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {t('quality.trust.title')}
      </h4>

      {/* Stacked bar chart */}
      <div
        className="flex h-4 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
        role="img"
        aria-label={t('quality.trust.title')}
      >
        {levels.map(({ key, barClass, percent }) => (
          <div
            key={key}
            className={`${barClass} transition-all duration-300`}
            style={{ width: `${percent}%` }}
            title={`${t(`quality.trust.${key}`)}: ${percent}%`}
          />
        ))}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs">
        {levels.map(({ key, labelKey, textClass, percent, count }) => (
          <div key={key} className="flex items-center gap-1.5">
            <div
              className={`w-2.5 h-2.5 rounded-full ${TRUST_LEVELS.find((l) => l.key === key)?.barClass}`}
            />
            <span className="text-gray-600 dark:text-gray-400">{t(labelKey)}</span>
            <span className={`font-medium ${textClass}`}>
              {percent}% <span className="text-gray-400">({count})</span>
            </span>
          </div>
        ))}
      </div>

      {/* Tooltip explanation */}
      <p className="text-xs text-gray-500 dark:text-gray-400 italic">
        {t('quality.trust.tooltip')}
      </p>
    </div>
  );
}
