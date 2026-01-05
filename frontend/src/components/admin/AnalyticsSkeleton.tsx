import { Skeleton } from '../Skeleton';

export function StatCardSkeleton() {
  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl p-6 border
                    border-gray-200 dark:border-gray-700"
    >
      <Skeleton height={14} width={100} className="mb-2" />
      <Skeleton height={32} width={80} className="mb-1" />
      <Skeleton height={12} width={60} />
    </div>
  );
}

export function AnalyticsOverviewSkeleton() {
  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
      aria-busy="true"
      aria-label="Loading analytics..."
    >
      {Array.from({ length: 4 }).map((_, i) => (
        <StatCardSkeleton key={i} />
      ))}
    </div>
  );
}

interface ChartSkeletonProps {
  height?: number;
}

export function ChartSkeleton({ height = 300 }: ChartSkeletonProps) {
  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl p-6 border
                    border-gray-200 dark:border-gray-700"
    >
      <Skeleton height={20} width={150} className="mb-4" />
      <Skeleton height={height} className="w-full" />
    </div>
  );
}

interface TableSkeletonProps {
  rows?: number;
}

export function TableSkeleton({ rows = 5 }: TableSkeletonProps) {
  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border
                    border-gray-200 dark:border-gray-700 overflow-hidden"
    >
      {/* Header */}
      <div
        className="border-b border-gray-200 dark:border-gray-700 p-4
                      flex gap-4"
      >
        <Skeleton height={16} className="w-1/4" />
        <Skeleton height={16} className="w-1/4" />
        <Skeleton height={16} className="w-1/4" />
        <Skeleton height={16} className="w-1/4" />
      </div>

      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="border-b border-gray-100 dark:border-gray-700/50
                                p-4 flex gap-4 last:border-0"
        >
          <Skeleton height={14} className="w-1/4" />
          <Skeleton height={14} className="w-1/4" />
          <Skeleton height={14} className="w-1/4" />
          <Skeleton height={14} className="w-1/4" />
        </div>
      ))}
    </div>
  );
}

export function ModerationCardSkeleton() {
  return (
    <div
      className="border border-gray-200 dark:border-gray-700 rounded-xl p-6
                 bg-white dark:bg-gray-800"
    >
      <div className="mb-4">
        <Skeleton height={24} className="w-3/4 mb-3" />
        <div className="flex flex-wrap gap-2 mb-3">
          <Skeleton width={80} height={24} className="rounded-full" />
          <Skeleton width={150} height={20} />
        </div>
        <div className="space-y-2">
          <Skeleton height={16} className="w-full" />
          <Skeleton height={16} className="w-4/5" />
        </div>
      </div>
      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <Skeleton width={100} height={36} className="rounded-lg" />
      </div>
    </div>
  );
}

interface ModerationListSkeletonProps {
  count?: number;
}

export function ModerationListSkeleton({ count = 3 }: ModerationListSkeletonProps) {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading items...">
      {Array.from({ length: count }).map((_, i) => (
        <ModerationCardSkeleton key={i} />
      ))}
    </div>
  );
}
