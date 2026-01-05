'use client';

import { useTranslation } from 'react-i18next';
import { Heart, Sun, AlertTriangle, HandHelping } from 'lucide-react';
import type { QualityType } from '@/types';

interface QualityChipsProps {
  selected: QualityType[];
  onChange: (qualities: QualityType[]) => void;
  disabled?: boolean;
  size?: 'sm' | 'md';
}

interface QualityConfig {
  key: QualityType;
  icon: React.ElementType;
  selectedClasses: string;
  iconSelectedClass: string;
}

const QUALITIES: QualityConfig[] = [
  {
    key: 'community_benefit',
    icon: Heart,
    selectedClasses:
      'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 ring-2 ring-rose-400',
    iconSelectedClass: 'text-rose-500',
  },
  {
    key: 'quality_of_life',
    icon: Sun,
    selectedClasses:
      'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 ring-2 ring-amber-400',
    iconSelectedClass: 'text-amber-500',
  },
  {
    key: 'urgent',
    icon: AlertTriangle,
    selectedClasses:
      'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 ring-2 ring-red-400',
    iconSelectedClass: 'text-red-500',
  },
  {
    key: 'would_volunteer',
    icon: HandHelping,
    selectedClasses:
      'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300 ring-2 ring-emerald-400',
    iconSelectedClass: 'text-emerald-500',
  },
];

const unselectedClasses =
  'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600';

export function QualityChips({
  selected,
  onChange,
  disabled = false,
  size = 'md',
}: QualityChipsProps) {
  const { t } = useTranslation();

  const toggleQuality = (quality: QualityType) => {
    if (disabled) return;
    const newSelected = selected.includes(quality)
      ? selected.filter((q) => q !== quality)
      : [...selected, quality];
    onChange(newSelected);
  };

  const sizeClasses = size === 'sm' ? 'px-2 py-1 text-xs gap-1' : 'px-3 py-1.5 text-sm gap-1.5';

  return (
    <div className="flex flex-wrap gap-2">
      {QUALITIES.map(({ key, icon: Icon, selectedClasses, iconSelectedClass }) => {
        const isSelected = selected.includes(key);
        return (
          <button
            key={key}
            type="button"
            onClick={() => toggleQuality(key)}
            disabled={disabled}
            className={`
              inline-flex items-center ${sizeClasses} rounded-full
              font-medium transition-all duration-200
              focus:outline-none focus:ring-2 focus:ring-offset-2
              ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
              ${isSelected ? selectedClasses : unselectedClasses}
            `}
            aria-pressed={isSelected}
          >
            <Icon className={`w-4 h-4 ${isSelected ? iconSelectedClass : ''}`} />
            <span>{t(`qualities.${key}`)}</span>
          </button>
        );
      })}
    </div>
  );
}
