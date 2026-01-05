'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { Download, FileJson, FileSpreadsheet, ChevronLeft } from 'lucide-react';
import { authAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { useToast } from '@/hooks/useToast';
import Link from 'next/link';

export default function DataExportPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { user } = useAuthStore();
  const { error: showError } = useToast();

  const [loading, setLoading] = useState(false);

  // Redirect if not logged in
  useEffect(() => {
    if (!user) {
      router.push('/signin?redirect=/settings/data');
    }
  }, [user, router]);

  if (!user) return null;

  const handleExport = async (format: 'json' | 'csv') => {
    setLoading(true);

    try {
      const blob = await authAPI.exportData(format);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `my_data_${user.id}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      showError(t('settings.data.exportError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageContainer maxWidth="2xl" paddingY="normal">
      <div className="mb-6">
        <Link
          href="/profile"
          className="inline-flex items-center text-sm text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
        >
          <ChevronLeft className="w-4 h-4 mr-1" />
          {t('common.back')}
        </Link>
      </div>

      <PageHeader title={t('settings.data.title')} description={t('settings.data.description')} />

      <Card className="mt-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Download className="w-5 h-5" />
          {t('settings.data.downloadTitle')}
        </h2>

        <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
          {t('settings.data.downloadDescription')}
        </p>

        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <Button
            onClick={() => handleExport('json')}
            disabled={loading}
            variant="secondary"
            className="flex items-center gap-2"
          >
            <FileJson className="w-4 h-4" />
            {t('settings.data.downloadJson')}
          </Button>

          <Button
            onClick={() => handleExport('csv')}
            disabled={loading}
            variant="secondary"
            className="flex items-center gap-2"
          >
            <FileSpreadsheet className="w-4 h-4" />
            {t('settings.data.downloadCsv')}
          </Button>
        </div>

        <p className="text-xs text-gray-500 dark:text-gray-500 mb-6">
          {t('settings.data.rateLimit')}
        </p>

        <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
          <h3 className="font-medium mb-3">{t('settings.data.whatIncluded')}</h3>
          <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-2 list-disc list-inside">
            <li>{t('settings.data.includesProfile')}</li>
            <li>{t('settings.data.includesIdeas')}</li>
            <li>{t('settings.data.includesComments')}</li>
            <li>{t('settings.data.includesVotes')}</li>
            <li>{t('settings.data.includesConsent')}</li>
          </ul>
        </div>
      </Card>

      <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700">
        <p className="text-sm text-gray-600 dark:text-gray-400">{t('settings.data.law25Notice')}</p>
      </div>

      <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700">
        <Link
          href="/settings/delete-account"
          className="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
        >
          {t('settings.data.deleteAccountLink')}
        </Link>
      </div>
    </PageContainer>
  );
}
