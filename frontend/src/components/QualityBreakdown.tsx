'use client';

import { useTranslation } from 'react-i18next';
import { Heart, Sun, AlertTriangle, HandHelping } from 'lucide-react';
import type { QualityCounts } from '@/types';

interface QualityBreakdownProps {
  counts: QualityCounts;
  totalUpvotes: number;
}

interface QualityConfig {
  key: keyof QualityCounts;
  icon: React.ElementType;
  bgClass: string;
  iconClass: string;
  countClass: string;
}

const QUALITIES: QualityConfig[] = [
  {
    key: 'community_benefit',
    icon: Heart,
    bgClass: 'bg-rose-100 dark:bg-rose-900/30',
    iconClass: 'text-rose-500',
    countClass: 'text-rose-600 dark:text-rose-400',
  },
  {
    key: 'quality_of_life',
    icon: Sun,
    bgClass: 'bg-amber-100 dark:bg-amber-900/30',
    iconClass: 'text-amber-500',
    countClass: 'text-amber-600 dark:text-amber-400',
  },
  {
    key: 'urgent',
    icon: AlertTriangle,
    bgClass: 'bg-red-100 dark:bg-red-900/30',
    iconClass: 'text-red-500',
    countClass: 'text-red-600 dark:text-red-400',
  },
  {
    key: 'would_volunteer',
    icon: HandHelping,
    bgClass: 'bg-emerald-100 dark:bg-emerald-900/30',
    iconClass: 'text-emerald-500',
    countClass: 'text-emerald-600 dark:text-emerald-400',
  },
];

export function QualityBreakdown({ counts, totalUpvotes }: QualityBreakdownProps) {
  const { t } = useTranslation();

  // Don't show if no upvotes
  if (totalUpvotes === 0) return null;

  // Check if any qualities have counts
  const hasAnyQualities = QUALITIES.some((q) => counts[q.key] > 0);
  if (!hasAnyQualities) return null;

  return (
    <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
        {t('qualities.breakdown')}
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {QUALITIES.map(({ key, icon: Icon, bgClass, iconClass, countClass }) => {
          const count = counts[key];
          if (count === 0) return null;

          return (
            <div key={key} className="flex items-center gap-2 text-sm">
              <div className={`p-1.5 rounded-full ${bgClass}`}>
                <Icon className={`w-4 h-4 ${iconClass}`} />
              </div>
              <span className="text-gray-600 dark:text-gray-400">{t(`qualities.${key}`)}</span>
              <span className={`font-semibold ${countClass}`}>{count}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
