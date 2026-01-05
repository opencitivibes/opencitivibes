'use client';

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/Card';
import { analyticsAPI } from '@/lib/api';
import type { TopContributorsResponse, ContributorType } from '@/types';
import { Trophy, Lightbulb, ThumbsUp, MessageSquare, Star } from 'lucide-react';

interface TopContributorsTableProps {
  initialType?: ContributorType;
}

const TYPE_ICONS: Record<ContributorType, React.ComponentType<{ className?: string }>> = {
  ideas: Lightbulb,
  votes: ThumbsUp,
  comments: MessageSquare,
  score: Star,
};

const TYPE_COLORS: Record<ContributorType, string> = {
  ideas:
    'bg-purple-100 dark:bg-purple-900/50 text-purple-800 dark:text-purple-300 border-purple-300 dark:border-purple-700',
  votes:
    'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300 border-green-300 dark:border-green-700',
  comments:
    'bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-700',
  score:
    'bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-700',
};

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="h-12 w-full bg-gray-100 dark:bg-gray-700 rounded animate-pulse" />
      ))}
    </div>
  );
}

function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-yellow-400 text-yellow-900 text-xs font-semibold">
        <Trophy className="h-3 w-3" />
        1st
      </span>
    );
  }
  if (rank === 2) {
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full bg-gray-300 text-gray-800 text-xs font-semibold">
        2nd
      </span>
    );
  }
  if (rank === 3) {
    return (
      <span className="inline-flex items-center px-2 py-1 rounded-full bg-amber-600 text-white text-xs font-semibold">
        3rd
      </span>
    );
  }
  return (
    <span className="inline-flex items-center px-2 py-1 rounded-full border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 text-xs font-medium">
      {rank}
    </span>
  );
}

export function TopContributorsTable({ initialType = 'ideas' }: TopContributorsTableProps) {
  const { t } = useTranslation();
  const [activeType, setActiveType] = useState<ContributorType>(initialType);
  const [data, setData] = useState<TopContributorsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await analyticsAPI.getTopContributors({
          type: activeType,
          limit: 10,
        });
        setData(response);
      } catch (err) {
        console.error('Failed to fetch contributors:', err);
        setError(t('analytics.error'));
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [activeType, t]);

  const types: ContributorType[] = ['ideas', 'votes', 'comments', 'score'];

  const getTypeLabel = (type: ContributorType): string => {
    switch (type) {
      case 'ideas':
        return t('analytics.topIdeaAuthors');
      case 'votes':
        return t('analytics.topVoters');
      case 'comments':
        return t('analytics.topCommenters');
      case 'score':
        return t('analytics.highestRated');
      default:
        return t('analytics.topContributors');
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('analytics.topContributors')}</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Type Selector */}
        <div className="flex flex-wrap gap-2 mb-4">
          {types.map((type) => {
            const Icon = TYPE_ICONS[type];
            const isActive = activeType === type;
            return (
              <button
                key={type}
                onClick={() => setActiveType(type)}
                className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                  isActive
                    ? TYPE_COLORS[type]
                    : 'bg-gray-50 dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                <Icon className="h-4 w-4" />
                {getTypeLabel(type)}
              </button>
            );
          })}
        </div>

        {/* Table */}
        {isLoading ? (
          <TableSkeleton />
        ) : error ? (
          <div className="text-center text-red-600 py-8">{error}</div>
        ) : !data || data.contributors.length === 0 ? (
          <div className="text-center text-gray-500 dark:text-gray-400 py-8">
            {t('analytics.noData')}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="py-3 px-4 text-left text-sm font-semibold text-gray-600 dark:text-gray-400 w-16">
                    {t('analytics.rank')}
                  </th>
                  <th className="py-3 px-4 text-left text-sm font-semibold text-gray-600 dark:text-gray-400">
                    {t('analytics.user')}
                  </th>
                  <th className="py-3 px-4 text-right text-sm font-semibold text-gray-600 dark:text-gray-400">
                    {activeType === 'score' ? t('analytics.score') : t('analytics.count')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.contributors.map((contributor) => (
                  <tr
                    key={contributor.user_id}
                    className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                  >
                    <td className="py-3 px-4">
                      <RankBadge rank={contributor.rank} />
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-col">
                        <span className="font-medium text-gray-900 dark:text-gray-100">
                          {contributor.display_name}
                        </span>
                        <span className="text-sm text-gray-500 dark:text-gray-400">
                          @{contributor.username}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right font-semibold text-gray-900 dark:text-gray-100">
                      {contributor.count.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
