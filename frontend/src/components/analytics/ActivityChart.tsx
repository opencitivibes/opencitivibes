'use client';

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/Card';
import { Button } from '@/components/Button';
import { Lightbulb, ThumbsUp, MessageSquare, Users } from 'lucide-react';
import type { TrendsResponse } from '@/types';

interface ActivityChartProps {
  data: TrendsResponse | null;
  isLoading: boolean;
}

type ChartMetric = 'ideas' | 'votes' | 'comments' | 'users';

const COLORS: Record<ChartMetric, string> = {
  ideas: '#8b5cf6', // Purple
  votes: '#22c55e', // Green
  comments: '#3b82f6', // Blue
  users: '#f59e0b', // Amber
};

const ICONS: Record<ChartMetric, React.ComponentType<{ className?: string }>> = {
  ideas: Lightbulb,
  votes: ThumbsUp,
  comments: MessageSquare,
  users: Users,
};

function ChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <div className="h-6 w-48 bg-gray-200 rounded animate-pulse" />
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full bg-gray-100 rounded animate-pulse" />
      </CardContent>
    </Card>
  );
}

export function ActivityChart({ data, isLoading }: ActivityChartProps) {
  const { t } = useTranslation();
  const [activeMetrics, setActiveMetrics] = useState<Set<ChartMetric>>(
    () => new Set<ChartMetric>(['ideas', 'votes'])
  );
  const [chartType, setChartType] = useState<'line' | 'area'>('area');

  const toggleMetric = (metric: ChartMetric) => {
    const newMetrics = new Set(activeMetrics);
    if (newMetrics.has(metric)) {
      if (newMetrics.size > 1) {
        newMetrics.delete(metric);
      }
    } else {
      newMetrics.add(metric);
    }
    setActiveMetrics(newMetrics);
  };

  if (isLoading) {
    return <ChartSkeleton />;
  }

  if (!data || data.data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics.trends')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-gray-500">
            {t('analytics.noData')}
          </div>
        </CardContent>
      </Card>
    );
  }

  const metrics: ChartMetric[] = ['ideas', 'votes', 'comments', 'users'];

  const ChartComponent = chartType === 'area' ? AreaChart : LineChart;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{t('analytics.trends')}</CardTitle>
        <div className="flex gap-2">
          <Button
            variant={chartType === 'area' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setChartType('area')}
          >
            {t('analytics.chartTypeArea')}
          </Button>
          <Button
            variant={chartType === 'line' ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setChartType('line')}
          >
            {t('analytics.chartTypeLine')}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {/* Metric Toggles */}
        <div className="flex flex-wrap gap-2 mb-4">
          {metrics.map((metric) => {
            const Icon = ICONS[metric];
            const isActive = activeMetrics.has(metric);
            return (
              <button
                key={metric}
                onClick={() => toggleMetric(metric)}
                className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  isActive ? 'text-white shadow-md' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                style={{
                  backgroundColor: isActive ? COLORS[metric] : undefined,
                  borderColor: COLORS[metric],
                }}
              >
                <Icon className="h-4 w-4" />
                {t(`analytics.metric_${metric}`)}
              </button>
            );
          })}
        </div>

        {/* Chart */}
        <div className="h-[300px]" role="img" aria-label={t('analytics.trends')}>
          <ResponsiveContainer width="100%" height="100%">
            <ChartComponent data={data.data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-gray-200" />
              <XAxis dataKey="period" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 12 }} tickLine={false} axisLine={false} width={40} />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                labelStyle={{ fontWeight: 'bold' }}
              />
              <Legend />
              {metrics.map((metric) =>
                activeMetrics.has(metric) ? (
                  chartType === 'area' ? (
                    <Area
                      key={metric}
                      type="monotone"
                      dataKey={metric}
                      stroke={COLORS[metric]}
                      fill={COLORS[metric]}
                      fillOpacity={0.2}
                      strokeWidth={2}
                      name={t(`analytics.metric_${metric}`)}
                    />
                  ) : (
                    <Line
                      key={metric}
                      type="monotone"
                      dataKey={metric}
                      stroke={COLORS[metric]}
                      strokeWidth={2}
                      dot={false}
                      name={t(`analytics.metric_${metric}`)}
                    />
                  )
                ) : null
              )}
            </ChartComponent>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
