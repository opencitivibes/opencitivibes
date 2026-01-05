'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import type { UserRole, UserFilterParams } from '@/types';

interface UserFiltersProps {
  filters: UserFilterState;
  onChange: (filters: UserFilterState) => void;
  onClear: () => void;
}

export interface UserFilterState {
  role?: UserRole;
  is_official?: boolean;
  is_banned?: boolean;
  trust_score_min?: number;
  trust_score_max?: number;
  vote_score_min?: number;
  vote_score_max?: number;
  has_penalties?: boolean;
  has_active_penalties?: boolean;
  created_after?: string;
  created_before?: string;
}

export const emptyFilterState: UserFilterState = {};

export function countActiveFilters(filters: UserFilterState): number {
  let count = 0;
  if (filters.role) count++;
  if (filters.is_official !== undefined) count++;
  if (filters.is_banned !== undefined) count++;
  if (filters.trust_score_min !== undefined || filters.trust_score_max !== undefined) count++;
  if (filters.vote_score_min !== undefined || filters.vote_score_max !== undefined) count++;
  if (filters.has_penalties !== undefined) count++;
  if (filters.has_active_penalties !== undefined) count++;
  if (filters.created_after || filters.created_before) count++;
  return count;
}

export function filtersToParams(
  filters: UserFilterState,
  page: number,
  pageSize: number,
  search?: string
): UserFilterParams {
  return {
    page,
    page_size: pageSize,
    search: search || undefined,
    include_inactive: true,
    role: filters.role,
    is_official: filters.is_official,
    is_banned: filters.is_banned,
    trust_score_min: filters.trust_score_min,
    trust_score_max: filters.trust_score_max,
    vote_score_min: filters.vote_score_min,
    vote_score_max: filters.vote_score_max,
    has_penalties: filters.has_penalties,
    has_active_penalties: filters.has_active_penalties,
    created_after: filters.created_after,
    created_before: filters.created_before,
  };
}

export function UserFilters({ filters, onChange, onClear }: UserFiltersProps) {
  const { t } = useTranslation();
  const [isExpanded, setIsExpanded] = useState(false);
  const activeCount = countActiveFilters(filters);

  const handleRoleChange = (role: UserRole | '') => {
    onChange({ ...filters, role: role || undefined });
  };

  const handleOfficialChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      ...filters,
      is_official: value === '' ? undefined : value === 'true',
    });
  };

  const handleBannedChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      ...filters,
      is_banned: value === '' ? undefined : value === 'true',
    });
  };

  const handleTrustScoreChange = (min: number | undefined, max: number | undefined) => {
    onChange({
      ...filters,
      trust_score_min: min,
      trust_score_max: max,
    });
  };

  const handleVoteScoreChange = (min: number | undefined, max: number | undefined) => {
    onChange({
      ...filters,
      vote_score_min: min,
      vote_score_max: max,
    });
  };

  const handlePenaltiesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...filters,
      has_penalties: e.target.checked ? true : undefined,
    });
  };

  const handleActivePenaltiesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...filters,
      has_active_penalties: e.target.checked ? true : undefined,
    });
  };

  const handleDateChange = (after: string | undefined, before: string | undefined) => {
    onChange({
      ...filters,
      created_after: after,
      created_before: before,
    });
  };

  // Quick filter presets
  const applyLowTrust = () => {
    onChange({ ...emptyFilterState, trust_score_max: 40 });
  };

  const applyBanned = () => {
    onChange({ ...emptyFilterState, is_banned: true });
  };

  const applyOfficials = () => {
    onChange({ ...emptyFilterState, is_official: true });
  };

  const applyNewUsers = () => {
    const sevenDaysAgo = new Date();
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    onChange({ ...emptyFilterState, created_after: sevenDaysAgo.toISOString().split('T')[0] });
  };

  return (
    <div className="bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 mb-4">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-700 dark:text-gray-300">
            {t('admin.users.filters.title')}
          </span>
          {activeCount > 0 && (
            <Badge variant="primary" className="text-xs">
              {t('admin.users.filters.activeCount', { count: activeCount })}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {activeCount > 0 && (
            <Button variant="ghost" size="sm" onClick={onClear}>
              {t('admin.users.filters.clear')}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-expanded={isExpanded}
          >
            {isExpanded ? t('admin.users.filters.collapse') : t('admin.users.filters.expand')}
            <svg
              className={`ml-1 w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </Button>
        </div>
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Quick Filters */}
          <div className="flex flex-wrap gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400 mr-2">
              {t('admin.users.filters.quickFilters')}:
            </span>
            <button
              onClick={applyLowTrust}
              className="px-3 py-1 text-xs rounded-full bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-300 hover:bg-error-200 dark:hover:bg-error-900/50 transition-colors"
            >
              {t('admin.users.filters.lowTrust')}
            </button>
            <button
              onClick={applyBanned}
              className="px-3 py-1 text-xs rounded-full bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-300 hover:bg-error-200 dark:hover:bg-error-900/50 transition-colors"
            >
              {t('admin.users.filters.banned')}
            </button>
            <button
              onClick={applyOfficials}
              className="px-3 py-1 text-xs rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-900/50 transition-colors"
            >
              {t('admin.users.filters.officials')}
            </button>
            <button
              onClick={applyNewUsers}
              className="px-3 py-1 text-xs rounded-full bg-info-100 dark:bg-info-900/30 text-info-700 dark:text-info-300 hover:bg-info-200 dark:hover:bg-info-900/50 transition-colors"
            >
              {t('admin.users.filters.newUsers')}
            </button>
          </div>

          {/* Filter Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {/* Role */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('admin.users.filters.role')}
              </label>
              <select
                value={filters.role || ''}
                onChange={(e) => handleRoleChange(e.target.value as UserRole | '')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">{t('admin.users.filters.allRoles')}</option>
                <option value="regular">{t('admin.users.filters.regularUser')}</option>
                <option value="category_admin">{t('admin.users.filters.categoryAdmin')}</option>
                <option value="global_admin">{t('admin.users.filters.globalAdmin')}</option>
                <option value="official">{t('admin.users.filters.official')}</option>
              </select>
            </div>

            {/* Official Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('admin.users.filters.officialStatus')}
              </label>
              <select
                value={filters.is_official === undefined ? '' : filters.is_official.toString()}
                onChange={handleOfficialChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">{t('admin.users.filters.allStatuses')}</option>
                <option value="true">{t('admin.users.filters.officialOnly')}</option>
                <option value="false">{t('admin.users.filters.nonOfficial')}</option>
              </select>
            </div>

            {/* Ban Status */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('admin.users.filters.banStatus')}
              </label>
              <select
                value={filters.is_banned === undefined ? '' : filters.is_banned.toString()}
                onChange={handleBannedChange}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">{t('admin.users.filters.allStatuses')}</option>
                <option value="true">{t('admin.users.filters.isBanned')}</option>
                <option value="false">{t('admin.users.filters.notBanned')}</option>
              </select>
            </div>

            {/* Trust Score Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('admin.users.filters.trustScore')}
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  min={0}
                  max={100}
                  placeholder={t('admin.users.filters.minScore')}
                  value={filters.trust_score_min ?? ''}
                  onChange={(e) =>
                    handleTrustScoreChange(
                      e.target.value ? parseInt(e.target.value) : undefined,
                      filters.trust_score_max
                    )
                  }
                  className="w-1/2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
                <input
                  type="number"
                  min={0}
                  max={100}
                  placeholder={t('admin.users.filters.maxScore')}
                  value={filters.trust_score_max ?? ''}
                  onChange={(e) =>
                    handleTrustScoreChange(
                      filters.trust_score_min,
                      e.target.value ? parseInt(e.target.value) : undefined
                    )
                  }
                  className="w-1/2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>

            {/* Vote Score Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('admin.users.filters.voteScore')}
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  placeholder={t('admin.users.filters.minScore')}
                  value={filters.vote_score_min ?? ''}
                  onChange={(e) =>
                    handleVoteScoreChange(
                      e.target.value ? parseInt(e.target.value) : undefined,
                      filters.vote_score_max
                    )
                  }
                  className="w-1/2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
                <input
                  type="number"
                  placeholder={t('admin.users.filters.maxScore')}
                  value={filters.vote_score_max ?? ''}
                  onChange={(e) =>
                    handleVoteScoreChange(
                      filters.vote_score_min,
                      e.target.value ? parseInt(e.target.value) : undefined
                    )
                  }
                  className="w-1/2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>

            {/* Date Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('admin.users.filters.registeredBetween')}
              </label>
              <div className="flex gap-2">
                <input
                  type="date"
                  value={filters.created_after?.split('T')[0] || ''}
                  onChange={(e) =>
                    handleDateChange(e.target.value || undefined, filters.created_before)
                  }
                  className="w-1/2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
                <input
                  type="date"
                  value={filters.created_before?.split('T')[0] || ''}
                  onChange={(e) =>
                    handleDateChange(filters.created_after, e.target.value || undefined)
                  }
                  className="w-1/2 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                />
              </div>
            </div>

            {/* Penalty Checkboxes */}
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.has_penalties ?? false}
                  onChange={handlePenaltiesChange}
                  className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {t('admin.users.filters.hasPenalties')}
                </span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.has_active_penalties ?? false}
                  onChange={handleActivePenaltiesChange}
                  className="w-4 h-4 rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500"
                />
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  {t('admin.users.filters.hasActivePenalties')}
                </span>
              </label>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
