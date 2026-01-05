import { IdeaListSkeleton } from '../IdeaCardSkeleton';

export function HomePageSkeleton() {
  return (
    <div className="animate-pulse">
      {/* Hero skeleton with fixed height to prevent CLS */}
      <div className="h-64 sm:h-80 md:h-96 bg-gray-300" />

      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <div className="h-10 bg-gray-200 rounded w-1/3 mb-8" />
            <IdeaListSkeleton count={5} />
          </div>
          <div className="lg:col-span-1">
            <div className="h-8 bg-gray-200 rounded w-2/3 mb-4" />
            <div className="space-y-2">
              {Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="h-6 bg-gray-200 rounded w-20" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export function IdeaDetailSkeleton() {
  return (
    <div className="animate-pulse max-w-4xl mx-auto px-4 py-8">
      {/* Breadcrumb skeleton */}
      <div className="h-4 bg-gray-200 rounded w-32 mb-6" />

      {/* Title skeleton */}
      <div className="h-10 bg-gray-200 rounded w-3/4 mb-4" />

      {/* Meta info skeleton */}
      <div className="flex gap-4 mb-6">
        <div className="h-6 w-24 bg-gray-200 rounded" />
        <div className="h-6 w-32 bg-gray-200 rounded" />
      </div>

      {/* Content skeleton */}
      <div className="space-y-3 mb-8">
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-5/6" />
        <div className="h-4 bg-gray-200 rounded w-4/6" />
      </div>

      {/* Voting skeleton */}
      <div className="flex gap-4 mb-8">
        <div className="h-10 w-24 bg-gray-200 rounded" />
        <div className="h-10 w-24 bg-gray-200 rounded" />
      </div>

      {/* Comments skeleton */}
      <div className="h-8 bg-gray-200 rounded w-32 mb-4" />
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="p-4 bg-gray-100 rounded-lg">
            <div className="h-4 bg-gray-200 rounded w-24 mb-2" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-200 rounded w-full" />
              <div className="h-3 bg-gray-200 rounded w-5/6" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function SearchPageSkeleton() {
  return (
    <div className="animate-pulse max-w-4xl mx-auto px-4 py-8">
      {/* Search bar skeleton */}
      <div className="h-12 bg-gray-200 rounded-lg w-full mb-8" />

      {/* Filters skeleton */}
      <div className="flex gap-4 mb-6">
        <div className="h-10 w-32 bg-gray-200 rounded" />
        <div className="h-10 w-32 bg-gray-200 rounded" />
      </div>

      {/* Results skeleton */}
      <IdeaListSkeleton count={5} />
    </div>
  );
}
