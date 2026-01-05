import type { Metadata } from 'next';
import { generateStaticMetadata, getSiteConfig } from '@/lib/seo/metadata';
import { generateWebPageSchema, generateBreadcrumbSchema } from '@/lib/seo/structured-data';
import { StructuredData } from '@/components/seo/StructuredData';
import ContactPageClient from '@/components/pages/ContactPageClient';

const siteConfig = getSiteConfig();

export const metadata: Metadata = generateStaticMetadata(
  {
    fr: 'Nous contacter',
    en: 'Contact Us',
  },
  {
    fr: `Contactez ${siteConfig.name.fr}. Questions, suggestions ou signalement de problèmes.`,
    en: `Contact ${siteConfig.name.en}. Questions, suggestions, or report issues.`,
  },
  'fr',
  '/contact'
);

const pageSchema = generateWebPageSchema(
  'Nous contacter',
  `Contactez ${siteConfig.name.fr}.`,
  `${siteConfig.url}/contact`,
  'ContactPage',
  'fr'
);

const breadcrumbSchema = generateBreadcrumbSchema([
  { name: 'Accueil', url: siteConfig.url },
  { name: 'Nous contacter', url: `${siteConfig.url}/contact` },
]);

export default function ContactPage() {
  return (
    <>
      <StructuredData data={[pageSchema, breadcrumbSchema]} />
      <ContactPageClient />
    </>
  );
}
