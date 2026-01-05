'use client';

import { useConfigTranslation } from '@/hooks/useConfigTranslation';
import { Card } from '@/components/Card';

export default function HowItWorks() {
  const { t, entityName } = useConfigTranslation();

  // Build step1 description with entity name
  const step1Desc = t('sidebar.step1Desc').replace('{{config.entityName}}', entityName);

  return (
    <Card>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
        <svg
          className="w-5 h-5 text-primary-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
          />
        </svg>
        {t('sidebar.howItWorks', 'How It Works')}
      </h3>
      <ol className="space-y-4">
        <li className="flex gap-3">
          <div className="flex-shrink-0 w-8 h-8 bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded-full flex items-center justify-center font-bold text-sm">
            1
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">
              {t('sidebar.step1Title', 'Submit an Idea')}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400" suppressHydrationWarning>
              {step1Desc}
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <div className="flex-shrink-0 w-8 h-8 bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded-full flex items-center justify-center font-bold text-sm">
            2
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">
              {t('sidebar.step2Title', 'Vote & Discuss')}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('sidebar.step2Desc', 'The community votes and comments on ideas')}
            </p>
          </div>
        </li>
        <li className="flex gap-3">
          <div className="flex-shrink-0 w-8 h-8 bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded-full flex items-center justify-center font-bold text-sm">
            3
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">
              {t('sidebar.step3Title', 'Gain Visibility')}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('sidebar.step3Desc', 'Popular ideas get noticed by decision makers')}
            </p>
          </div>
        </li>
      </ol>
    </Card>
  );
}
