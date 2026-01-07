'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import { ideaAPI } from '@/lib/api';
import { TrustBreakdown } from '@/components/TrustBreakdown';
import { QualityBreakdown } from '@/components/QualityBreakdown';
import type { QualitySignalsResponse } from '@/types';

interface QualitySignalsPanelProps {
  ideaId: number;
  expanded?: boolean;
  refreshKey?: number;
  /** Show expanded by default for admins */
  isAdmin?: boolean;
}

export function QualitySignalsPanel({
  ideaId,
  expanded: initialExpanded,
  refreshKey = 0,
  isAdmin = false,
}: QualitySignalsPanelProps) {
  // Default: collapsed for regular users, expanded for admins
  const defaultExpanded = initialExpanded ?? isAdmin;
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(defaultExpanded);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signals, setSignals] = useState<QualitySignalsResponse | null>(null);

  const fetchSignals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await ideaAPI.getQualitySignals(ideaId);
      setSignals(data);
    } catch (err) {
      console.error('Error fetching quality signals:', err);
      setError(t('common.error'));
    } finally {
      setLoading(false);
    }
  }, [ideaId, t]);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals, refreshKey]);

  const handleRetry = () => {
    fetchSignals();
  };

  const toggleExpanded = () => {
    setExpanded((prev) => !prev);
  };

  // Loading skeleton
  if (loading) {
    return (
      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl animate-pulse">
        <div className="flex items-center justify-between mb-4">
          <div className="h-5 w-32 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-5 w-5 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
        <div className="space-y-3">
          <div className="h-4 w-full bg-gray-200 dark:bg-gray-700 rounded-full" />
          <div className="flex gap-4">
            <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl">
        <div className="flex items-center justify-between">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          <button
            type="button"
            onClick={handleRetry}
            className="flex items-center gap-1.5 text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            {t('common.retry')}
          </button>
        </div>
      </div>
    );
  }

  // No data
  if (!signals || signals.total_upvotes === 0) {
    return null;
  }

  return (
    <section
      className="mt-6 bg-gray-50 dark:bg-gray-800/50 rounded-xl overflow-hidden"
      aria-labelledby="quality-signals-heading"
    >
      {/* Header with toggle */}
      <button
        type="button"
        onClick={toggleExpanded}
        className="flex items-center justify-between w-full p-4 text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset"
        aria-expanded={expanded}
        aria-controls="quality-signals-content"
      >
        <h3
          id="quality-signals-heading"
          className="text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          {t('quality.signals.title')}
        </h3>
        {expanded ? (
          <ChevronUp className="w-5 h-5 text-gray-500" aria-hidden="true" />
        ) : (
          <ChevronDown className="w-5 h-5 text-gray-500" aria-hidden="true" />
        )}
      </button>

      {/* Content */}
      {expanded && (
        <div id="quality-signals-content" className="px-4 pb-4 space-y-6">
          {/* Trust Distribution */}
          {signals.trust_distribution.total_votes > 0 && (
            <TrustBreakdown trustDistribution={signals.trust_distribution} />
          )}

          {/* Quality Counts (existing component) */}
          {signals.quality_counts && (
            <QualityBreakdown
              counts={signals.quality_counts}
              totalUpvotes={signals.total_upvotes}
            />
          )}
        </div>
      )}
    </section>
  );
}
