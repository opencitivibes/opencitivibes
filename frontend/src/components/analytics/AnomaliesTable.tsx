'use client';

import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import Link from 'next/link';
import { Card } from '@/components/Card';
import { ExternalLink, ArrowUpDown, AlertCircle, ChevronLeft, ChevronRight } from 'lucide-react';
import type { ScoreAnomaly } from '@/types';

interface AnomaliesTableProps {
  anomalies: ScoreAnomaly[];
  isLoading: boolean;
}

type SortField = 'divergence' | 'public_score' | 'weighted_score';
type SortDirection = 'asc' | 'desc';

const PAGE_SIZE = 10;

function getDivergenceBadgeClass(divergencePercent: number): string {
  const absDiv = Math.abs(divergencePercent);
  if (absDiv < 10) {
    return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
  }
  if (absDiv < 30) {
    return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300';
  }
  return 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300';
}

interface SortableHeaderProps {
  field: SortField;
  currentField: SortField;
  direction: SortDirection;
  onSort: (field: SortField) => void;
  children: React.ReactNode;
}

function SortableHeader({ field, currentField, direction, onSort, children }: SortableHeaderProps) {
  const isActive = field === currentField;
  return (
    <button
      onClick={() => onSort(field)}
      className="flex items-center gap-1 font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100"
    >
      {children}
      <ArrowUpDown
        className={`h-3.5 w-3.5 ${isActive ? 'text-blue-600 dark:text-blue-400' : 'text-gray-400'}`}
        aria-hidden="true"
      />
      <span className="sr-only">
        {isActive ? (direction === 'asc' ? ', sorted ascending' : ', sorted descending') : ''}
      </span>
    </button>
  );
}

export function AnomaliesTable({ anomalies, isLoading }: AnomaliesTableProps) {
  const { t } = useTranslation();
  const [sortField, setSortField] = useState<SortField>('divergence');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [currentPage, setCurrentPage] = useState(0);

  const sortedAnomalies = useMemo(() => {
    return [...anomalies].sort((a, b) => {
      let aVal: number, bVal: number;
      switch (sortField) {
        case 'divergence':
          aVal = Math.abs(a.divergence_percent);
          bVal = Math.abs(b.divergence_percent);
          break;
        case 'public_score':
          aVal = a.public_score;
          bVal = b.public_score;
          break;
        case 'weighted_score':
          aVal = a.weighted_score;
          bVal = b.weighted_score;
          break;
        default:
          return 0;
      }
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
    });
  }, [anomalies, sortField, sortDirection]);

  const paginatedAnomalies = useMemo(() => {
    const start = currentPage * PAGE_SIZE;
    return sortedAnomalies.slice(start, start + PAGE_SIZE);
  }, [sortedAnomalies, currentPage]);

  const totalPages = Math.ceil(anomalies.length / PAGE_SIZE);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
    setCurrentPage(0);
  };

  if (isLoading) {
    return <AnomaliesTableSkeleton />;
  }

  if (anomalies.length === 0) {
    return (
      <Card className="p-8 text-center">
        <AlertCircle className="h-12 w-12 text-green-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          {t('analytics.weightedScores.noAnomalies')}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {t('analytics.weightedScores.noAnomaliesDescription')}
        </p>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full" role="table">
          <thead className="bg-gray-50 dark:bg-gray-800/50">
            <tr>
              <th
                scope="col"
                className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                {t('analytics.weightedScores.idea')}
              </th>
              <th scope="col" className="px-4 py-3 text-right">
                <SortableHeader
                  field="public_score"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                >
                  <span className="text-xs uppercase tracking-wider">
                    {t('analytics.weightedScores.publicScore')}
                  </span>
                </SortableHeader>
              </th>
              <th scope="col" className="px-4 py-3 text-right">
                <SortableHeader
                  field="weighted_score"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                >
                  <span className="text-xs uppercase tracking-wider">
                    {t('analytics.weightedScores.weightedScore')}
                  </span>
                </SortableHeader>
              </th>
              <th scope="col" className="px-4 py-3 text-right">
                <SortableHeader
                  field="divergence"
                  currentField={sortField}
                  direction={sortDirection}
                  onSort={handleSort}
                >
                  <span className="text-xs uppercase tracking-wider">
                    {t('analytics.weightedScores.divergence')}
                  </span>
                </SortableHeader>
              </th>
              <th
                scope="col"
                className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
              >
                {t('common.actions')}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {paginatedAnomalies.map((anomaly) => (
              <tr key={anomaly.idea_id} className="hover:bg-gray-50 dark:hover:bg-gray-800/30">
                <td className="px-4 py-3">
                  <div className="max-w-xs">
                    <p className="font-medium text-gray-900 dark:text-gray-100 truncate">
                      {anomaly.title}
                    </p>
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="font-mono text-gray-900 dark:text-gray-100">
                    {anomaly.public_score}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <span className="font-mono text-gray-900 dark:text-gray-100">
                    {anomaly.weighted_score.toFixed(1)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <span
                    className={`inline-flex px-2 py-0.5 text-sm font-semibold rounded ${getDivergenceBadgeClass(anomaly.divergence_percent)}`}
                  >
                    {anomaly.divergence_percent >= 0 ? '+' : ''}
                    {anomaly.divergence_percent.toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/ideas/${anomaly.idea_id}`}
                    className="inline-flex items-center gap-1 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    {t('analytics.weightedScores.viewIdea')}
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/30">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('admin.showingOf', {
              showing: `${currentPage * PAGE_SIZE + 1}-${Math.min((currentPage + 1) * PAGE_SIZE, anomalies.length)}`,
              total: anomalies.length,
            })}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              disabled={currentPage === 0}
              className="p-2 rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={t('common.previous')}
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1}
              className="p-2 rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label={t('common.next')}
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </Card>
  );
}

function AnomaliesTableSkeleton() {
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-800/50">
            <tr>
              {[1, 2, 3, 4, 5].map((i) => (
                <th key={i} className="px-4 py-3">
                  <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {[1, 2, 3, 4, 5].map((i) => (
              <tr key={i}>
                <td className="px-4 py-3">
                  <div className="h-5 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                  <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mt-1" />
                </td>
                <td className="px-4 py-3">
                  <div className="h-5 w-12 bg-gray-200 dark:bg-gray-700 rounded animate-pulse ml-auto" />
                </td>
                <td className="px-4 py-3">
                  <div className="h-5 w-12 bg-gray-200 dark:bg-gray-700 rounded animate-pulse ml-auto" />
                </td>
                <td className="px-4 py-3">
                  <div className="h-5 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse ml-auto" />
                </td>
                <td className="px-4 py-3">
                  <div className="h-5 w-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse ml-auto" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
