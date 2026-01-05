'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Card } from '@/components/Card';
import AdminNotificationsPanel from '@/components/admin/AdminNotificationsPanel';

export default function AdminNotificationsPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
    }
  }, [user, router]);

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="4xl" paddingY="normal">
      <PageHeader title={t('admin.notifications.title', 'System Notifications')} />
      <Card>
        <AdminNotificationsPanel />
      </Card>
    </PageContainer>
  );
}
