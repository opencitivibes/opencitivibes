export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="flex flex-col items-center space-y-4">
        {/* Animated spinner */}
        <div className="relative">
          <div className="w-12 h-12 border-4 border-primary-200 dark:border-primary-800 rounded-full"></div>
          <div className="w-12 h-12 border-4 border-primary-600 dark:border-primary-400 rounded-full border-t-transparent animate-spin absolute top-0 left-0"></div>
        </div>
        {/* Loading skeleton */}
        <div className="w-48 h-4 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
      </div>
    </div>
  );
}
