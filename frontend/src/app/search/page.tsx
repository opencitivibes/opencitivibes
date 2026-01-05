'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { SearchBar, SearchFilters, SearchResults } from '@/components/search';
import { HeroBanner } from '@/components/HeroBanner';
import { searchAPI, categoryAPI } from '@/lib/api';
import type {
  SearchResults as SearchResultsType,
  SearchFilters as FilterType,
  Category,
} from '@/types';

const RESULTS_PER_PAGE = 20;

function SearchPageContent() {
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();

  // State
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [results, setResults] = useState<SearchResultsType | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [filters, setFilters] = useState<FilterType>(() => {
    const categoryId = searchParams.get('category_id');
    const minScore = searchParams.get('min_score');
    const hasComments = searchParams.get('has_comments');
    const fromDate = searchParams.get('from_date');
    const toDate = searchParams.get('to_date');
    const language = searchParams.get('language');

    return {
      category_id: categoryId ? parseInt(categoryId) : undefined,
      min_score: minScore ? parseInt(minScore) : undefined,
      has_comments: hasComments === 'true' ? true : undefined,
      from_date: fromDate || undefined,
      to_date: toDate || undefined,
      language: language || undefined,
    };
  });

  // Load categories on mount
  useEffect(() => {
    categoryAPI.getAll().then(setCategories).catch(console.error);
  }, []);

  // Update URL with current state
  const updateURL = useCallback(
    (q: string, f: FilterType) => {
      const params = new URLSearchParams();
      if (q) params.set('q', q);
      if (f.category_id) params.set('category_id', f.category_id.toString());
      if (f.min_score !== undefined) params.set('min_score', f.min_score.toString());
      if (f.has_comments) params.set('has_comments', 'true');
      if (f.from_date) params.set('from_date', f.from_date);
      if (f.to_date) params.set('to_date', f.to_date);
      if (f.language) params.set('language', f.language);

      const queryString = params.toString();
      router.push(queryString ? `/search?${queryString}` : '/search', { scroll: false });
    },
    [router]
  );

  // Search function
  const performSearch = useCallback(
    async (q: string, f: FilterType, page = 0) => {
      if (q.length < 2) {
        setResults(null);
        setSearchError(null);
        return;
      }

      setIsLoading(true);
      setSearchError(null);

      try {
        const data = await searchAPI.searchIdeas({
          q,
          filters: f,
          skip: page * RESULTS_PER_PAGE,
          limit: RESULTS_PER_PAGE,
          highlight: true,
        });

        if (page === 0) {
          setResults(data);
        } else {
          // Append results for pagination
          setResults((prev) =>
            prev
              ? {
                  ...data,
                  results: [...prev.results, ...data.results],
                }
              : data
          );
        }
      } catch (error) {
        console.error('Search failed:', error);
        setSearchError(t('search.searchError'));
        setResults(null);
      } finally {
        setIsLoading(false);
      }
    },
    [t]
  );

  // Search on mount if query present
  useEffect(() => {
    if (query && query.length >= 2) {
      performSearch(query, filters, 0);
    }
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle search
  const handleSearch = useCallback(
    (newQuery: string) => {
      setQuery(newQuery);
      setCurrentPage(0);
      updateURL(newQuery, filters);
      performSearch(newQuery, filters, 0);
    },
    [filters, updateURL, performSearch]
  );

  // Handle filter change
  const handleFilterChange = useCallback(
    (newFilters: FilterType) => {
      setFilters(newFilters);
      setCurrentPage(0);
      updateURL(query, newFilters);
      if (query && query.length >= 2) {
        performSearch(query, newFilters, 0);
      }
    },
    [query, updateURL, performSearch]
  );

  // Handle clear filters
  const handleClearFilters = useCallback(() => {
    const emptyFilters: FilterType = {};
    setFilters(emptyFilters);
    setCurrentPage(0);
    updateURL(query, emptyFilters);
    if (query && query.length >= 2) {
      performSearch(query, emptyFilters, 0);
    }
  }, [query, updateURL, performSearch]);

  // Handle load more
  const handleLoadMore = useCallback(() => {
    const nextPage = currentPage + 1;
    setCurrentPage(nextPage);
    performSearch(query, filters, nextPage);
  }, [currentPage, query, filters, performSearch]);

  const hasMore = results ? results.results.length < results.total : false;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Hero Banner */}
      <HeroBanner showButtons={false} />

      <div className="max-w-4xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-6">
          {t('search.title')}
        </h1>

        {/* Search bar */}
        <div className="mb-6">
          <SearchBar
            initialQuery={query}
            onSearch={handleSearch}
            autoFocus={!query}
            showAutocomplete={true}
          />
        </div>

        {/* Filters */}
        <div className="mb-6">
          <SearchFilters
            filters={filters}
            categories={categories}
            onChange={handleFilterChange}
            onClear={handleClearFilters}
          />
        </div>

        {/* Results */}
        <SearchResults
          results={results}
          isLoading={isLoading}
          query={query}
          onLoadMore={handleLoadMore}
          hasMore={hasMore}
          error={searchError}
          onRetry={() => performSearch(query, filters, 0)}
        />
      </div>
    </div>
  );
}

// Wrap with Suspense for useSearchParams
export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
        </div>
      }
    >
      <SearchPageContent />
    </Suspense>
  );
}
