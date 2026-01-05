import type { Metadata } from 'next';
import { generateStaticMetadata, siteConfig } from '@/lib/seo/metadata';
import { generateWebPageSchema, generateBreadcrumbSchema } from '@/lib/seo/structured-data';
import { StructuredData } from '@/components/seo/StructuredData';
import TermsPageClient from '@/components/pages/TermsPageClient';

export const metadata: Metadata = generateStaticMetadata(
  {
    fr: "Conditions d'utilisation",
    en: 'Terms of Service',
  },
  {
    fr: "Conditions d'utilisation de Idées pour Montréal. Règles de conduite et responsabilités des utilisateurs.",
    en: 'Terms of Service for Ideas for Montreal. Code of conduct and user responsibilities.',
  },
  'fr',
  '/terms'
);

const pageSchema = generateWebPageSchema(
  "Conditions d'utilisation",
  "Conditions d'utilisation de Idées pour Montréal.",
  `${siteConfig.url}/terms`,
  'WebPage',
  'fr'
);

const breadcrumbSchema = generateBreadcrumbSchema([
  { name: 'Accueil', url: siteConfig.url },
  { name: "Conditions d'utilisation", url: `${siteConfig.url}/terms` },
]);

export default function TermsPage() {
  return (
    <>
      <StructuredData data={[pageSchema, breadcrumbSchema]} />
      <TermsPageClient />
    </>
  );
}
