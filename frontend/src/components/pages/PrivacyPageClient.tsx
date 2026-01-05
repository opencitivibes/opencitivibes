'use client';

import { useTranslation } from 'react-i18next';
import LegalPageContent from './LegalPageContent';

export default function PrivacyPageClient() {
  const { t } = useTranslation();

  return <LegalPageContent documentType="privacy" title={t('legal.privacyTitle')} />;
}
