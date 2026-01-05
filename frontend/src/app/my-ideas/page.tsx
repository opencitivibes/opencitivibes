'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useConfigTranslation } from '@/hooks/useConfigTranslation';
import { useAuthStore } from '@/store/authStore';
import { ideaAPI } from '@/lib/api';
import IdeaCard from '@/components/IdeaCard';
import { Button } from '@/components/Button';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import type { Idea } from '@/types';

export default function MyIdeasPage() {
  const { t, tc } = useConfigTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);

  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      router.push('/signin?redirect=/my-ideas');
      return;
    }

    loadMyIdeas();
  }, [user, router]);

  const loadMyIdeas = async () => {
    try {
      const data = await ideaAPI.getMyIdeas();
      setIdeas(data);
    } catch (error) {
      console.error('Error loading my ideas:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (!user) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <PageHeader
        title={t('ideas.myIdeas')}
        description={t('ideas.myIdeasDescription', 'View and manage all your submitted ideas')}
        actions={
          <Button variant="primary" onClick={() => router.push('/submit')}>
            + {t('nav.submitIdea')}
          </Button>
        }
      />

      {/* Ideas List */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-primary-500"></div>
          <p className="mt-4 text-gray-500">{t('common.loading')}</p>
        </div>
      ) : ideas.length === 0 ? (
        <div className="text-center py-16 bg-white dark:bg-gray-800 rounded-xl shadow-md border border-gray-100 dark:border-gray-700">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary-50 dark:bg-primary-900/30 mb-6">
            <svg
              className="w-10 h-10 text-primary-500 dark:text-primary-400"
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
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            {t('ideas.noIdeasYet', 'No ideas yet')}
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">
            {tc('ideas.noIdeasMessage')}
          </p>
          <Button variant="primary" onClick={() => router.push('/submit')}>
            {t('ideas.submitFirstIdea', 'Submit Your First Idea')}
          </Button>
        </div>
      ) : (
        <div className="space-y-4">
          {ideas.map((idea) => (
            <IdeaCard
              key={idea.id}
              idea={idea}
              onVoteUpdate={loadMyIdeas}
              onClick={() => router.push(`/ideas/${idea.id}`)}
            />
          ))}
        </div>
      )}
    </PageContainer>
  );
}
