'use client';

import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { PageContainer } from '@/components/PageContainer';
import { Button } from '@/components/Button';
import { Home, Search } from 'lucide-react';

export function NotFoundContent() {
  const { t } = useTranslation();

  return (
    <PageContainer maxWidth="lg" paddingY="xl">
      <div className="text-center py-16">
        {/* Visual indicator */}
        <div className="inline-flex items-center justify-center w-24 h-24 rounded-full bg-primary-100 dark:bg-primary-900/40 mb-8">
          <span className="text-5xl font-bold text-primary-600 dark:text-primary-400">404</span>
        </div>

        <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
          {t('errors.notFound.title')}
        </h1>

        <p className="text-lg text-gray-600 dark:text-gray-300 mb-8 max-w-md mx-auto">
          {t('errors.notFound.description')}
        </p>

        {/* Recovery options */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/">
            <Button variant="primary">
              <Home className="w-4 h-4 mr-2" aria-hidden="true" />
              {t('errors.notFound.backHome')}
            </Button>
          </Link>
          <Link href="/search">
            <Button variant="secondary">
              <Search className="w-4 h-4 mr-2" aria-hidden="true" />
              {t('errors.notFound.search')}
            </Button>
          </Link>
        </div>
      </div>
    </PageContainer>
  );
}
