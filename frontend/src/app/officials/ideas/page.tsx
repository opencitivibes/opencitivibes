'use client';

import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { officialsAPI, categoryAPI } from '@/lib/api';
import type { OfficialsIdeaWithQualityStats, Category } from '@/types';
import { Download, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import Link from 'next/link';

export default function OfficialsIdeasPage() {
  const { t } = useTranslation();
  const { getCategoryName } = useLocalizedField();
  const [ideas, setIdeas] = useState<OfficialsIdeaWithQualityStats[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [qualityFilter, setQualityFilter] = useState<string>('');
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [minQualityCount, setMinQualityCount] = useState(0);
  const [minQualityInput, setMinQualityInput] = useState('0');
  const [sortBy, setSortBy] = useState<'quality_count' | 'score' | 'created_at'>('quality_count');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [page, setPage] = useState(0);
  const limit = 20;

  const fetchIdeas = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await officialsAPI.getIdeas({
        quality_filter: qualityFilter || undefined,
        category_id: categoryId,
        min_quality_count: minQualityCount,
        sort_by: sortBy,
        sort_order: sortOrder,
        skip: page * limit,
        limit,
      });
      setIdeas(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Failed to fetch ideas:', error);
    } finally {
      setIsLoading(false);
    }
  }, [qualityFilter, categoryId, minQualityCount, sortBy, sortOrder, page]);

  useEffect(() => {
    fetchIdeas();
  }, [fetchIdeas]);

  useEffect(() => {
    categoryAPI.getAll().then((res) => setCategories(res));
  }, []);

  const handleExport = () => {
    officialsAPI.exportIdeasCSV({
      quality_filter: qualityFilter || undefined,
      category_id: categoryId,
      min_quality_count: minQualityCount,
    });
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t('officials.ideasExplorer')}
        </h2>
        <button
          onClick={handleExport}
          title={t('officials.exportMobileWarning')}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Download className="w-4 h-4" />
          {t('officials.exportCSV')}
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-4 h-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('officials.filters')}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Quality Filter */}
          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
              {t('officials.qualityFilter')}
            </label>
            <select
              value={qualityFilter}
              onChange={(e) => {
                setQualityFilter(e.target.value);
                setPage(0);
              }}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">{t('officials.allQualities')}</option>
              <option value="community_benefit">{t('qualities.community_benefit')}</option>
              <option value="quality_of_life">{t('qualities.quality_of_life')}</option>
              <option value="urgent">{t('qualities.urgent')}</option>
              <option value="would_volunteer">{t('qualities.would_volunteer')}</option>
            </select>
          </div>

          {/* Category Filter */}
          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
              {t('officials.category')}
            </label>
            <select
              value={categoryId || ''}
              onChange={(e) => {
                setCategoryId(e.target.value ? Number(e.target.value) : undefined);
                setPage(0);
              }}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="">{t('officials.allCategories')}</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {getCategoryName(cat)}
                </option>
              ))}
            </select>
          </div>

          {/* Min Quality Count */}
          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
              {t('officials.minQualityCount')}
            </label>
            <input
              type="number"
              min={0}
              value={minQualityInput}
              onChange={(e) => {
                setMinQualityInput(e.target.value);
                const val = e.target.value === '' ? 0 : parseInt(e.target.value, 10);
                setMinQualityCount(isNaN(val) ? 0 : Math.max(0, val));
                setPage(0);
              }}
              onBlur={() => {
                // Normalize the display value on blur to remove leading zeros
                setMinQualityInput(String(minQualityCount));
              }}
              onFocus={(e) => e.target.select()}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>

          {/* Sort By */}
          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
              {t('officials.sortBy')}
            </label>
            <select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [field, order] = e.target.value.split('-');
                setSortBy(field as typeof sortBy);
                setSortOrder(order as typeof sortOrder);
                setPage(0);
              }}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              <option value="quality_count-desc">{t('officials.sortQualityDesc')}</option>
              <option value="quality_count-asc">{t('officials.sortQualityAsc')}</option>
              <option value="score-desc">{t('officials.sortScoreDesc')}</option>
              <option value="score-asc">{t('officials.sortScoreAsc')}</option>
              <option value="created_at-desc">{t('officials.sortNewest')}</option>
              <option value="created_at-asc">{t('officials.sortOldest')}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
          </div>
        ) : ideas.length === 0 ? (
          <div className="text-center py-12 text-gray-500">{t('officials.noIdeasFound')}</div>
        ) : (
          <>
            {/* Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-700/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                      {t('officials.title')}
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                      {t('officials.score')}
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                      {t('officials.qualityCount')}
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                      {t('officials.created')}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {ideas.map((idea) => (
                    <tr key={idea.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                      <td className="px-4 py-3">
                        <Link
                          href={`/officials/ideas/${idea.id}`}
                          className="text-sm font-medium text-gray-900 dark:text-white hover:text-primary-600"
                        >
                          {idea.title}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                        {idea.score}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300">
                          {idea.quality_count}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {new Date(idea.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {t('officials.showing', {
                  from: page * limit + 1,
                  to: Math.min((page + 1) * limit, total),
                  total,
                })}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  disabled={page === 0}
                  className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
                  aria-label={t('common.previous')}
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= totalPages - 1}
                  className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
                  aria-label={t('common.next')}
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
