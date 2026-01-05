'use client';

import { useTranslation } from 'react-i18next';
import LegalPageContent from './LegalPageContent';

export default function TermsPageClient() {
  const { t } = useTranslation();

  return <LegalPageContent documentType="terms" title={t('legal.termsTitle')} />;
}
