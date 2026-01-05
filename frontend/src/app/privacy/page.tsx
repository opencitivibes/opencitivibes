import type { Metadata } from 'next';
import { generateStaticMetadata, siteConfig } from '@/lib/seo/metadata';
import { generateWebPageSchema, generateBreadcrumbSchema } from '@/lib/seo/structured-data';
import { StructuredData } from '@/components/seo/StructuredData';
import PrivacyPageClient from '@/components/pages/PrivacyPageClient';

export const metadata: Metadata = generateStaticMetadata(
  {
    fr: 'Politique de confidentialité',
    en: 'Privacy Policy',
  },
  {
    fr: 'Politique de confidentialité de Idées pour Montréal. Découvrez comment nous protégeons vos données personnelles.',
    en: 'Privacy Policy for Ideas for Montreal. Learn how we protect your personal data.',
  },
  'fr',
  '/privacy'
);

const pageSchema = generateWebPageSchema(
  'Politique de confidentialité',
  'Politique de confidentialité de Idées pour Montréal.',
  `${siteConfig.url}/privacy`,
  'WebPage',
  'fr'
);

const breadcrumbSchema = generateBreadcrumbSchema([
  { name: 'Accueil', url: siteConfig.url },
  { name: 'Politique de confidentialité', url: `${siteConfig.url}/privacy` },
]);

export default function PrivacyPage() {
  return (
    <>
      <StructuredData data={[pageSchema, breadcrumbSchema]} />
      <PrivacyPageClient />
    </>
  );
}
