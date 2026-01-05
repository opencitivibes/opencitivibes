'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/Button';
import { Calendar, RefreshCw } from 'lucide-react';
import type { DateRange, DateRangePreset, Granularity } from '@/types';

interface DateRangeSelectorProps {
  dateRange: DateRange;
  granularity: Granularity;
  onDateRangeChange: (range: DateRange) => void;
  onGranularityChange: (granularity: Granularity) => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

export function DateRangeSelector({
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  dateRange,
  granularity,
  onDateRangeChange,
  onGranularityChange,
  onRefresh,
  isRefreshing = false,
}: DateRangeSelectorProps) {
  // Note: dateRange is passed for API compatibility; component manages preset state internally
  const { t } = useTranslation();
  const [selectedPreset, setSelectedPreset] = useState<DateRangePreset>('last30days');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');

  const handlePresetChange = (preset: DateRangePreset) => {
    setSelectedPreset(preset);

    const today = new Date();
    let startDate: Date;
    let endDate: Date = today;

    switch (preset) {
      case 'last7days':
        startDate = new Date(today);
        startDate.setDate(today.getDate() - 7);
        break;
      case 'last30days':
        startDate = new Date(today);
        startDate.setDate(today.getDate() - 30);
        break;
      case 'last90days':
        startDate = new Date(today);
        startDate.setDate(today.getDate() - 90);
        break;
      case 'thisYear':
        startDate = new Date(today.getFullYear(), 0, 1);
        break;
      case 'lastYear':
        startDate = new Date(today.getFullYear() - 1, 0, 1);
        endDate = new Date(today.getFullYear() - 1, 11, 31);
        break;
      case 'allTime':
        startDate = new Date(2020, 0, 1); // Platform start date
        break;
      case 'custom':
        return; // Don't update, let user pick dates
      default:
        startDate = new Date(today);
        startDate.setDate(today.getDate() - 30);
    }

    onDateRangeChange({ startDate, endDate });
  };

  const handleCustomDateApply = () => {
    if (customStart && customEnd) {
      onDateRangeChange({
        startDate: new Date(customStart),
        endDate: new Date(customEnd),
      });
    }
  };

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="flex flex-wrap gap-4">
        {/* Date Range Preset */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('analytics.customRange')}
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400 dark:text-gray-500">
              <Calendar className="h-4 w-4" />
            </div>
            <select
              value={selectedPreset}
              onChange={(e) => handlePresetChange(e.target.value as DateRangePreset)}
              className="block w-full pl-10 pr-10 py-2 text-base text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-lg bg-white dark:bg-gray-800 border shadow-sm"
            >
              <option value="last7days">{t('analytics.last7Days')}</option>
              <option value="last30days">{t('analytics.last30Days')}</option>
              <option value="last90days">{t('analytics.last90Days')}</option>
              <option value="thisYear">{t('analytics.thisYear')}</option>
              <option value="lastYear">{t('analytics.lastYear')}</option>
              <option value="allTime">{t('analytics.allTime')}</option>
              <option value="custom">{t('analytics.customRange')}</option>
            </select>
          </div>
        </div>

        {/* Custom Date Inputs (visible when custom selected) */}
        {selectedPreset === 'custom' && (
          <>
            <div className="space-y-2">
              <label
                htmlFor="start-date"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                {t('analytics.startDate')}
              </label>
              <input
                id="start-date"
                type="date"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="end-date"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                {t('analytics.endDate')}
              </label>
              <input
                id="end-date"
                type="date"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
              />
            </div>
            <div className="flex items-end">
              <Button
                onClick={handleCustomDateApply}
                disabled={!customStart || !customEnd}
                size="sm"
              >
                {t('analytics.apply')}
              </Button>
            </div>
          </>
        )}

        {/* Granularity */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('analytics.granularity')}
          </label>
          <select
            value={granularity}
            onChange={(e) => onGranularityChange(e.target.value as Granularity)}
            className="block w-full px-3 py-2 text-base text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm rounded-lg bg-white dark:bg-gray-800 border shadow-sm"
          >
            <option value="day">{t('analytics.daily')}</option>
            <option value="week">{t('analytics.weekly')}</option>
            <option value="month">{t('analytics.monthly')}</option>
          </select>
        </div>
      </div>

      {/* Refresh Button */}
      <Button variant="secondary" onClick={onRefresh} disabled={isRefreshing} size="sm">
        <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin mr-2' : 'mr-2'}`} />
        {t('analytics.refresh')}
      </Button>
    </div>
  );
}
