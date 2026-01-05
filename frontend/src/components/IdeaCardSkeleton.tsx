import { Skeleton } from './Skeleton';

export function IdeaCardSkeleton() {
  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200
                 dark:border-gray-700 p-4 shadow-sm"
      aria-label="Loading idea..."
      role="article"
      aria-busy="true"
    >
      <div className="flex gap-4">
        {/* Vote buttons skeleton */}
        <div className="flex flex-col items-center gap-1 flex-shrink-0">
          <Skeleton variant="circular" width={36} height={36} />
          <Skeleton width={28} height={20} className="rounded" />
          <Skeleton variant="circular" width={36} height={36} />
        </div>

        {/* Content skeleton */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Title */}
          <Skeleton height={24} className="w-4/5" />

          {/* Description lines */}
          <div className="space-y-2">
            <Skeleton height={16} className="w-full" />
            <Skeleton height={16} className="w-5/6" />
          </div>

          {/* Tags */}
          <div className="flex gap-2 flex-wrap">
            <Skeleton width={70} height={24} className="rounded-full" />
            <Skeleton width={90} height={24} className="rounded-full" />
            <Skeleton width={60} height={24} className="rounded-full" />
          </div>

          {/* Meta info */}
          <div className="flex items-center gap-4 pt-2">
            <Skeleton width={120} height={14} />
            <Skeleton width={80} height={14} />
          </div>
        </div>
      </div>
    </div>
  );
}

interface IdeaListSkeletonProps {
  count?: number;
}

export function IdeaListSkeleton({ count = 5 }: IdeaListSkeletonProps) {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading ideas...">
      {Array.from({ length: count }).map((_, i) => (
        <IdeaCardSkeleton key={i} />
      ))}
    </div>
  );
}

export default IdeaCardSkeleton;
