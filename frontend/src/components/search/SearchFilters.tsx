'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { usePlatformConfig } from '@/lib/config/PlatformConfigProvider';
import type { SearchFilters as FilterType, Category } from '@/types';

interface SearchFiltersProps {
  filters: FilterType;
  categories: Category[];
  onChange: (filters: FilterType) => void;
  onClear: () => void;
}

export function SearchFilters({ filters, categories, onChange, onClear }: SearchFiltersProps) {
  const { t } = useTranslation();
  const { getCategoryName } = useLocalizedField();
  const { config } = usePlatformConfig();
  const [showDatePicker, setShowDatePicker] = useState(false);

  // Get supported languages from platform config
  const supportedLocales = config?.localization?.supported_locales || ['fr', 'en'];

  const activeFilterCount = Object.entries(filters).filter(
    ([, v]) => v !== undefined && v !== null && v !== '' && !(Array.isArray(v) && v.length === 0)
  ).length;

  const handleCategoryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      ...filters,
      category_id: value ? parseInt(value) : undefined,
    });
  };

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      ...filters,
      language: value || undefined,
    });
  };

  const handleMinScoreChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    onChange({
      ...filters,
      min_score: value ? parseInt(value) : undefined,
    });
  };

  const handleHasCommentsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...filters,
      has_comments: e.target.checked ? true : undefined,
    });
  };

  const handleDateChange = (field: 'from_date' | 'to_date', value: string) => {
    onChange({
      ...filters,
      [field]: value || undefined,
    });
  };

  return (
    <div className="space-y-4">
      {/* Main filters row */}
      <div className="flex flex-wrap gap-3 items-center">
        {/* Category filter */}
        <div className="relative">
          <select
            value={filters.category_id?.toString() || ''}
            onChange={handleCategoryChange}
            className="appearance-none bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 pr-8 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:border-primary-500 transition-colors"
          >
            <option value="">{t('search.filters.allCategories')}</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {getCategoryName(cat)}
              </option>
            ))}
          </select>
          <svg
            className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>

        {/* Language filter */}
        <div className="relative">
          <select
            value={filters.language || ''}
            onChange={handleLanguageChange}
            className="appearance-none bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-2 pr-8 text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:border-primary-500 transition-colors"
          >
            <option value="">{t('search.filters.allLanguages')}</option>
            {supportedLocales.map((locale) => (
              <option key={locale} value={locale}>
                {t(`search.filters.${locale}`)}
              </option>
            ))}
          </select>
          <svg
            className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>

        {/* Date range button */}
        <button
          type="button"
          onClick={() => setShowDatePicker(!showDatePicker)}
          className={`flex items-center gap-2 px-4 py-2 text-sm border rounded-lg transition-colors ${
            filters.from_date || filters.to_date
              ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
              : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800'
          }`}
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          {t('search.filters.dateRange')}
          {(filters.from_date || filters.to_date) && (
            <span className="ml-1 w-2 h-2 rounded-full bg-primary-500" />
          )}
        </button>

        {/* Min score filter */}
        <div className="flex items-center gap-2">
          <label htmlFor="minScore" className="text-sm text-gray-600 dark:text-gray-400">
            {t('search.filters.minScore')}:
          </label>
          <input
            id="minScore"
            type="number"
            min="0"
            value={filters.min_score ?? ''}
            onChange={handleMinScoreChange}
            className="w-20 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:border-primary-500"
            placeholder="0"
          />
        </div>

        {/* Has comments checkbox */}
        <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={filters.has_comments === true}
            onChange={handleHasCommentsChange}
            className="w-4 h-4 text-primary-600 border-gray-300 dark:border-gray-600 rounded focus:ring-primary-500 bg-white dark:bg-gray-800"
          />
          {t('search.filters.hasComments')}
        </label>

        {/* Clear filters */}
        {activeFilterCount > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="flex items-center gap-1 px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
            {t('search.filters.clear')} ({activeFilterCount})
          </button>
        )}
      </div>

      {/* Date picker row */}
      {showDatePicker && (
        <div className="flex flex-wrap gap-4 items-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <label htmlFor="fromDate" className="text-sm text-gray-600 dark:text-gray-400">
              {t('search.filters.from')}:
            </label>
            <input
              id="fromDate"
              type="date"
              value={filters.from_date || ''}
              onChange={(e) => handleDateChange('from_date', e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:border-primary-500"
            />
          </div>
          <div className="flex items-center gap-2">
            <label htmlFor="toDate" className="text-sm text-gray-600 dark:text-gray-400">
              {t('search.filters.to')}:
            </label>
            <input
              id="toDate"
              type="date"
              value={filters.to_date || ''}
              onChange={(e) => handleDateChange('to_date', e.target.value)}
              className="px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 focus:border-primary-500"
            />
          </div>
          {(filters.from_date || filters.to_date) && (
            <button
              type="button"
              onClick={() =>
                onChange({
                  ...filters,
                  from_date: undefined,
                  to_date: undefined,
                })
              }
              className="text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
            >
              {t('search.filters.clearDates')}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default SearchFilters;
