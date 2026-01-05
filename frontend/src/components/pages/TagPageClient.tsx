'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import IdeaCard from '@/components/IdeaCard';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import api from '@/lib/api';
import type { Idea } from '@/types';

const PAGE_SIZE = 10;

interface TagPageClientProps {
  tagName: string;
}

export default function TagPageClient({ tagName }: TagPageClientProps) {
  const { t } = useTranslation();
  const router = useRouter();
  const decodedTagName = decodeURIComponent(tagName);

  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [hasMore, setHasMore] = useState(true);
  const [tagId, setTagId] = useState<number | null>(null);
  const [tagStats, setTagStats] = useState<{
    total_ideas: number;
    approved_ideas: number;
  } | null>(null);

  const pageRef = useRef(0);

  const loadInitialData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError('');
      pageRef.current = 0;

      // Get the tag by exact name
      let tag;
      try {
        const tagResponse = await api.get(`/tags/by-name/${encodeURIComponent(decodedTagName)}`);
        tag = tagResponse.data;
        setTagId(tag.id);
      } catch (tagErr) {
        const axiosError = tagErr as import('axios').AxiosError;
        if (axiosError.response?.status === 404) {
          setError(t('tags.notFound', 'Tag not found'));
          setIsLoading(false);
          return;
        }
        throw tagErr;
      }

      // Get tag statistics and first page of ideas in parallel
      const [statsResponse, ideasResponse] = await Promise.all([
        api.get(`/tags/${tag.id}/statistics`),
        api.get(`/tags/${tag.id}/ideas/full?skip=0&limit=${PAGE_SIZE}`),
      ]);

      setTagStats({
        total_ideas: statsResponse.data.total_ideas,
        approved_ideas: statsResponse.data.approved_ideas,
      });

      const fetchedIdeas = ideasResponse.data;
      setIdeas(fetchedIdeas);
      setHasMore(fetchedIdeas.length === PAGE_SIZE);
      pageRef.current = 1;
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error loading tag data:', err);
      setError(axiosError.response?.data?.detail || t('common.error'));
    } finally {
      setIsLoading(false);
    }
  }, [decodedTagName, t]);

  const loadMore = useCallback(async () => {
    if (!tagId || isLoadingMore || !hasMore) return;

    try {
      setIsLoadingMore(true);
      const skip = pageRef.current * PAGE_SIZE;
      const response = await api.get(`/tags/${tagId}/ideas/full?skip=${skip}&limit=${PAGE_SIZE}`);
      const newIdeas = response.data;

      setIdeas((prev) => [...prev, ...newIdeas]);
      setHasMore(newIdeas.length === PAGE_SIZE);
      pageRef.current += 1;
    } catch (err) {
      console.error('Error loading more ideas:', err);
    } finally {
      setIsLoadingMore(false);
    }
  }, [tagId, isLoadingMore, hasMore]);

  useEffect(() => {
    if (decodedTagName) {
      loadInitialData();
    }
  }, [decodedTagName, loadInitialData]);

  const handleIdeaClick = (ideaId: number) => {
    router.push(`/ideas/${ideaId}`);
  };

  if (isLoading) {
    return (
      <PageContainer>
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
          <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
          <div className="space-y-4 mt-8">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-48 bg-gray-200 dark:bg-gray-700 rounded"></div>
            ))}
          </div>
        </div>
      </PageContainer>
    );
  }

  if (error) {
    return (
      <PageContainer>
        <Alert variant="error">{error}</Alert>
        <div className="mt-4">
          <Button variant="secondary" onClick={() => router.push('/')}>
            {t('common.backToHome', 'Back to Home')}
          </Button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title={`#${decodedTagName}`}
        description={
          tagStats
            ? t('tags.ideaCount', `{{count}} approved idea(s) with this tag`, {
                count: tagStats.approved_ideas,
              })
            : ''
        }
      />

      {ideas.length === 0 ? (
        <Alert variant="info">{t('tags.noIdeas', 'No approved ideas found with this tag.')}</Alert>
      ) : (
        <div className="space-y-4">
          {ideas.map((idea) => (
            <IdeaCard
              key={idea.id}
              idea={idea}
              onClick={() => handleIdeaClick(idea.id)}
              onVoteUpdate={loadInitialData}
            />
          ))}

          {hasMore && (
            <div className="flex justify-center pt-4">
              <Button variant="secondary" onClick={loadMore} disabled={isLoadingMore}>
                {isLoadingMore
                  ? t('common.loading', 'Loading...')
                  : t('common.loadMore', 'Load More')}
              </Button>
            </div>
          )}
        </div>
      )}

      <div className="mt-8">
        <Button variant="secondary" onClick={() => router.push('/')}>
          {t('common.backToHome', 'Back to Home')}
        </Button>
      </div>
    </PageContainer>
  );
}
