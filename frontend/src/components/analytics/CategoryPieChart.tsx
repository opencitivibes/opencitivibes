'use client';

import { useTranslation } from 'react-i18next';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import type { PieLabelRenderProps } from 'recharts';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/Card';
import type { CategoriesAnalyticsResponse, CategoryAnalytics } from '@/types';

interface CategoryPieChartProps {
  data: CategoriesAnalyticsResponse | null;
  isLoading: boolean;
}

const COLORS = [
  '#8b5cf6', // Purple
  '#22c55e', // Green
  '#3b82f6', // Blue
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#ec4899', // Pink
  '#06b6d4', // Cyan
  '#84cc16', // Lime
  '#f97316', // Orange
  '#6366f1', // Indigo
];

interface ChartData {
  name: string;
  value: number;
  category: CategoryAnalytics;
  [key: string]: string | number | CategoryAnalytics;
}

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

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ payload: ChartData }>;
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  const { t } = useTranslation();

  if (active && payload && payload.length > 0 && payload[0]) {
    const data = payload[0].payload;
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-lg">
        <p className="font-semibold text-gray-900">{data.name}</p>
        <p className="text-sm text-gray-600">
          {t('analytics.totalIdeas')}: {data.value}
        </p>
        <p className="text-sm text-gray-600">
          {t('analytics.approvalRate')}: {(data.category.approval_rate * 100).toFixed(1)}%
        </p>
        <p className="text-sm text-gray-600">
          {t('analytics.avgScore')}: {data.category.avg_score.toFixed(1)}
        </p>
      </div>
    );
  }
  return null;
}

function renderCustomLabel(props: PieLabelRenderProps) {
  const { cx, cy, midAngle, innerRadius, outerRadius, percent } = props;

  // Handle undefined values
  if (
    typeof cx !== 'number' ||
    typeof cy !== 'number' ||
    typeof midAngle !== 'number' ||
    typeof innerRadius !== 'number' ||
    typeof outerRadius !== 'number' ||
    typeof percent !== 'number'
  ) {
    return null;
  }

  if (percent < 0.05) return null; // Don't show label for small slices

  const RADIAN = Math.PI / 180;
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor="middle"
      dominantBaseline="central"
      className="text-xs font-medium"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  );
}

export function CategoryPieChart({ data, isLoading }: CategoryPieChartProps) {
  const { t } = useTranslation();
  const { getCategoryName } = useLocalizedField();

  if (isLoading) {
    return <ChartSkeleton />;
  }

  if (!data || data.categories.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics.categoryDistribution')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-gray-500">
            {t('analytics.noData')}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Transform data for pie chart
  const chartData: ChartData[] = data.categories
    .filter((cat) => cat.total_ideas > 0)
    .map((cat) => ({
      name: getCategoryName(cat),
      value: cat.total_ideas,
      category: cat,
    }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('analytics.categoryDistribution')}</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          className="h-[280px] sm:h-[300px]"
          role="img"
          aria-label={t('analytics.categoryDistribution')}
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={renderCustomLabel}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                layout="horizontal"
                verticalAlign="bottom"
                align="center"
                wrapperStyle={{
                  fontSize: '10px',
                  paddingTop: '10px',
                  overflow: 'auto',
                  maxHeight: '80px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
