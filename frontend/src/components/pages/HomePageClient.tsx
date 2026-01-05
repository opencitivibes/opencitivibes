'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useConfigTranslation } from '@/hooks/useConfigTranslation';
import InfiniteScroll from 'react-infinite-scroll-component';
import IdeaCard from '@/components/IdeaCard';
import { IdeaCardSkeleton, IdeaListSkeleton } from '@/components/IdeaCardSkeleton';
import PopularTags from '@/components/PopularTags';
import HowItWorks from '@/components/HowItWorks';
import { Alert } from '@/components/Alert';
import { PageContainer } from '@/components/PageContainer';
import { HeroBanner } from '@/components/HeroBanner';
import { ideaAPI, categoryAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import type { Idea, Category } from '@/types';

export default function HomePageClient() {
  const { t, tc } = useConfigTranslation();
  const router = useRouter();
  const { getCategoryName } = useLocalizedField();
  const { sessionExpired, clearSessionExpired, accountDeleted, clearAccountDeleted } =
    useAuthStore();
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<number | undefined>();
  const [hasMore, setHasMore] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [showSessionExpiredAlert, setShowSessionExpiredAlert] = useState(false);
  const [showAccountDeletedAlert, setShowAccountDeletedAlert] = useState(false);

  const loadCategories = async () => {
    try {
      const data = await categoryAPI.getAll();
      setCategories(data);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const loadIdeas = async (reset = false) => {
    try {
      const skip = reset ? 0 : ideas.length;
      const newIdeas = await ideaAPI.getLeaderboard(selectedCategory, skip, 20);

      // Handle null response (e.g., from session expiration)
      if (!newIdeas) {
        setIsLoading(false);
        return;
      }

      if (reset) {
        setIdeas(newIdeas);
      } else {
        setIdeas([...ideas, ...newIdeas]);
      }

      if (newIdeas.length < 20) {
        setHasMore(false);
      }
    } catch (error) {
      console.error('Error loading ideas:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCategories();
  }, []);

  useEffect(() => {
    setIsLoading(true);
    setHasMore(true);
    loadIdeas(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategory]);

  // Handle session expiration
  useEffect(() => {
    if (sessionExpired) {
      setShowSessionExpiredAlert(true);
      // Auto-hide after 5 seconds
      const timer = setTimeout(() => {
        setShowSessionExpiredAlert(false);
        clearSessionExpired();
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [sessionExpired, clearSessionExpired]);

  // Handle account deletion confirmation
  // Check both Zustand store and sessionStorage for reliability across navigation
  useEffect(() => {
    const fromSessionStorage =
      typeof window !== 'undefined' && sessionStorage.getItem('accountDeleted') === 'true';

    if (accountDeleted || fromSessionStorage) {
      setShowAccountDeletedAlert(true);
      // Clear sessionStorage flag
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('accountDeleted');
      }
      // Clear Zustand state if set
      if (accountDeleted) {
        clearAccountDeleted();
      }
      // Auto-hide after 8 seconds
      const timer = setTimeout(() => {
        setShowAccountDeletedAlert(false);
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [accountDeleted, clearAccountDeleted]);

  const handleVoteUpdate = () => {
    loadIdeas(true);
  };

  return (
    <>
      {/* Hero Section */}
      <HeroBanner />

      <PageContainer maxWidth="7xl" paddingY="normal">
        {/* Session Expired Alert */}
        {showSessionExpiredAlert && (
          <div className="mb-6">
            <Alert
              variant="warning"
              dismissible
              onDismiss={() => {
                setShowSessionExpiredAlert(false);
                clearSessionExpired();
              }}
            >
              {t(
                'auth.sessionExpired',
                'Your session has expired. Please login again to continue.'
              )}
            </Alert>
          </div>
        )}

        {/* Account Deleted Confirmation */}
        {showAccountDeletedAlert && (
          <div className="mb-6">
            <Alert
              variant="success"
              dismissible
              onDismiss={() => setShowAccountDeletedAlert(false)}
            >
              {t(
                'settings.delete.success',
                'Your account has been successfully deleted. Thank you for being part of our community.'
              )}
            </Alert>
          </div>
        )}

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content - Ideas List */}
          <div className="lg:col-span-2">
            {/* Header */}
            <div className="mb-4 sm:mb-8">
              <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                {t('ideas.leaderboard')}
              </h2>
            </div>

            {/* Category Filter Pills */}
            <div className="flex gap-2 mb-4 sm:mb-8 overflow-x-auto pb-2 -mx-4 px-4 lg:mx-0 lg:px-0 lg:flex-wrap scrollbar-hide">
              {/* All Categories Button */}
              <button
                onClick={() => setSelectedCategory(undefined)}
                className={`
                  flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-shadow duration-200
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900
                  ${
                    !selectedCategory
                      ? 'bg-primary-500 text-white shadow-md'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }
                `}
              >
                {t('ideas.allCategories')}
              </button>

              {/* Category Buttons */}
              {categories.map((category) => (
                <button
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`
                    flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-shadow duration-200
                    focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900
                    ${
                      selectedCategory === category.id
                        ? 'bg-primary-500 text-white shadow-md'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }
                  `}
                >
                  {getCategoryName(category)}
                </button>
              ))}
            </div>

            {/* Ideas List with Infinite Scroll */}
            {isLoading && ideas.length === 0 ? (
              <IdeaListSkeleton count={5} />
            ) : ideas.length === 0 ? (
              <div className="text-center py-12">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-800 mb-4">
                  <svg
                    className="w-8 h-8 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                </div>
                <p className="text-gray-600 dark:text-gray-300 text-lg font-medium">
                  {t('ideas.noIdeas')}
                </p>
                <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
                  {t('ideas.beTheFirst', 'Be the first to submit an idea!')}
                </p>
              </div>
            ) : (
              <InfiniteScroll
                dataLength={ideas.length}
                next={() => loadIdeas(false)}
                hasMore={hasMore}
                loader={<IdeaCardSkeleton />}
                endMessage={
                  <div className="text-center py-6 border-t border-gray-200 dark:border-gray-700 mt-6">
                    <p className="text-gray-500 dark:text-gray-400 text-sm">
                      {ideas.length} {tc('ideas.showingCount', { count: ideas.length })}
                    </p>
                  </div>
                }
              >
                <div className="space-y-4 pt-1">
                  {ideas.map((idea, index) => (
                    <div
                      key={idea.id}
                      className="animate-fadeInUp"
                      style={{ animationDelay: `${Math.min(index * 50, 400)}ms` }}
                    >
                      <IdeaCard
                        idea={idea}
                        onVoteUpdate={handleVoteUpdate}
                        onClick={() => router.push(`/ideas/${idea.id}`)}
                        onCategoryClick={(categoryId) => setSelectedCategory(categoryId)}
                        hideStatus={true}
                      />
                    </div>
                  ))}
                </div>
              </InfiniteScroll>
            )}
          </div>

          {/* Sidebar */}
          <aside className="lg:col-span-1">
            <div className="sticky top-20 space-y-6">
              <HowItWorks />
              <PopularTags />
            </div>
          </aside>
        </div>
      </PageContainer>
    </>
  );
}
