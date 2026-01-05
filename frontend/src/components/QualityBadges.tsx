'use client';

import { useTranslation } from 'react-i18next';
import { AlertTriangle, HandHelping } from 'lucide-react';
import type { QualityCounts } from '@/types';

interface QualityBadgesProps {
  counts?: QualityCounts;
  threshold?: number; // Show badge if count >= threshold
}

interface BadgeConfig {
  key: string;
  qualityKey: keyof QualityCounts;
  icon: React.ElementType;
  bgClass: string;
  iconClass: string;
  ringClass: string;
}

// Only show the most important badges to avoid clutter
const BADGE_CONFIG: BadgeConfig[] = [
  {
    key: 'volunteer',
    qualityKey: 'would_volunteer',
    icon: HandHelping,
    bgClass: 'bg-emerald-100 dark:bg-emerald-900/50',
    iconClass: 'text-emerald-500',
    ringClass: 'ring-white dark:ring-gray-800',
  },
  {
    key: 'urgent',
    qualityKey: 'urgent',
    icon: AlertTriangle,
    bgClass: 'bg-red-100 dark:bg-red-900/50',
    iconClass: 'text-red-500',
    ringClass: 'ring-white dark:ring-gray-800',
  },
];

export function QualityBadges({ counts, threshold = 3 }: QualityBadgesProps) {
  const { t } = useTranslation();

  if (!counts) return null;

  // Filter badges that meet the threshold
  const activeBadges = BADGE_CONFIG.filter((badge) => counts[badge.qualityKey] >= threshold);

  if (activeBadges.length === 0) return null;

  return (
    <div
      className="absolute top-2 right-2 flex gap-1"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      {activeBadges.map(({ key, qualityKey, icon: Icon, bgClass, iconClass, ringClass }) => (
        <div
          key={key}
          className={`p-1 rounded-full ${bgClass} ring-2 ${ringClass}`}
          title={t(`qualities.${qualityKey}`)}
        >
          <Icon className={`w-3 h-3 ${iconClass}`} aria-hidden="true" />
          <span className="sr-only">{t(`qualities.${qualityKey}`)}</span>
        </div>
      ))}
    </div>
  );
}
