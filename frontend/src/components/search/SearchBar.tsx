'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useDebounce } from '@/hooks/useDebounce';
import { searchAPI } from '@/lib/api';
import type { AutocompleteResult, TagSuggestion } from '@/types';

interface SearchBarProps {
  initialQuery?: string;
  onSearch?: (query: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  showAutocomplete?: boolean;
  compact?: boolean;
}

export function SearchBar({
  initialQuery = '',
  onSearch,
  placeholder,
  autoFocus = false,
  showAutocomplete = true,
  compact = false,
}: SearchBarProps) {
  const { t } = useTranslation();
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [isLoading, setIsLoading] = useState(false);
  const [autocomplete, setAutocomplete] = useState<AutocompleteResult | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const debouncedQuery = useDebounce(query, 200);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Fetch autocomplete suggestions
  useEffect(() => {
    if (!showAutocomplete || debouncedQuery.length < 2) {
      setAutocomplete(null);
      return;
    }

    const fetchSuggestions = async () => {
      setIsLoading(true);
      try {
        const result = await searchAPI.getAutocomplete(debouncedQuery, 5);
        setAutocomplete(result);
        setShowDropdown(true);
      } catch {
        setAutocomplete(null);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSuggestions();
  }, [debouncedQuery, showAutocomplete]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Handle search submission
  const handleSearch = useCallback(
    (searchQuery: string) => {
      if (searchQuery.trim().length < 2) return;
      setShowDropdown(false);

      if (onSearch) {
        onSearch(searchQuery);
      } else {
        // Default: navigate to search page
        router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
      }
    },
    [onSearch, router]
  );

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    const suggestions = getSuggestionsList();
    const maxIndex = suggestions.length - 1;

    switch (e.key) {
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && suggestions[selectedIndex]) {
          const item = suggestions[selectedIndex];
          if (item.type === 'tag') {
            handleSearch(`#${item.value}`);
          } else {
            handleSearch(item.value);
          }
        } else {
          handleSearch(query);
        }
        break;
      case 'Escape':
        setShowDropdown(false);
        setQuery('');
        inputRef.current?.blur();
        break;
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => (prev < maxIndex ? prev + 1 : 0));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : maxIndex));
        break;
    }
  };

  // Build flat list of suggestions for keyboard navigation
  const getSuggestionsList = (): Array<{
    type: 'idea' | 'tag';
    value: string;
    display: string;
  }> => {
    if (!autocomplete) return [];
    const list: Array<{ type: 'idea' | 'tag'; value: string; display: string }> = [];

    autocomplete.ideas.forEach((idea) => {
      list.push({ type: 'idea', value: idea, display: idea });
    });

    autocomplete.tags.forEach((tag: TagSuggestion) => {
      list.push({ type: 'tag', value: tag.name, display: `#${tag.display_name}` });
    });

    return list;
  };

  const handleSuggestionClick = (type: 'idea' | 'tag', value: string) => {
    if (type === 'tag') {
      handleSearch(`#${value}`);
    } else {
      handleSearch(value);
    }
  };

  const suggestions = getSuggestionsList();
  const hasResults = suggestions.length > 0;

  return (
    <div className={`relative w-full ${compact ? 'max-w-xs' : 'max-w-xl'}`}>
      <div className="relative">
        {/* Search Icon */}
        <svg
          className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>

        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setSelectedIndex(-1);
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => hasResults && setShowDropdown(true)}
          placeholder={placeholder || t('search.placeholder')}
          className={`w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 !pr-10 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200 dark:focus:ring-primary-800 transition-colors placeholder:text-gray-400 dark:placeholder:text-gray-500 ${
            compact ? 'py-1.5 text-sm !pl-8' : 'py-2.5 !pl-10'
          }`}
          autoFocus={autoFocus}
          suppressHydrationWarning
        />

        {/* Clear/Loading button */}
        {query && (
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            onClick={() => {
              setQuery('');
              setAutocomplete(null);
              setShowDropdown(false);
              inputRef.current?.focus();
            }}
          >
            {isLoading ? (
              <svg className="h-4 w-4 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            ) : (
              <svg
                className="h-4 w-4 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            )}
          </button>
        )}
      </div>

      {/* Autocomplete Dropdown */}
      {showDropdown && hasResults && showAutocomplete && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg overflow-hidden"
        >
          {/* Idea suggestions */}
          {autocomplete?.ideas && autocomplete.ideas.length > 0 && (
            <div>
              <div className="px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase bg-gray-50 dark:bg-gray-900">
                {t('search.suggestions.ideas')}
              </div>
              {autocomplete.ideas.map((idea, index) => (
                <button
                  key={`idea-${idea}`}
                  type="button"
                  className={`w-full px-3 py-2 text-left text-sm hover:bg-primary-50 dark:hover:bg-primary-900/30 transition-colors flex items-center gap-2 text-gray-900 dark:text-gray-100 ${
                    selectedIndex === index ? 'bg-primary-50 dark:bg-primary-900/30' : ''
                  }`}
                  onClick={() => handleSuggestionClick('idea', idea)}
                >
                  <svg
                    className="h-4 w-4 text-gray-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                  <span className="truncate">{idea}</span>
                </button>
              ))}
            </div>
          )}

          {/* Tag suggestions */}
          {autocomplete?.tags && autocomplete.tags.length > 0 && (
            <div>
              <div className="px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400 uppercase bg-gray-50 dark:bg-gray-900">
                {t('search.suggestions.tags')}
              </div>
              {autocomplete.tags.map((tag: TagSuggestion, index) => (
                <button
                  key={`tag-${tag.name}`}
                  type="button"
                  className={`w-full px-3 py-2 text-left text-sm hover:bg-primary-50 dark:hover:bg-primary-900/30 transition-colors flex items-center justify-between text-gray-900 dark:text-gray-100 ${
                    selectedIndex === (autocomplete?.ideas?.length || 0) + index
                      ? 'bg-primary-50 dark:bg-primary-900/30'
                      : ''
                  }`}
                  onClick={() => handleSuggestionClick('tag', tag.name)}
                >
                  <span className="flex items-center gap-2">
                    <span className="text-primary-600 dark:text-primary-400">#</span>
                    <span>{tag.display_name}</span>
                  </span>
                  <span className="text-xs text-gray-400">{tag.idea_count} ideas</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default SearchBar;
