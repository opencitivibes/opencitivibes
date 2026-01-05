import type { Metadata } from 'next';
import { generateStaticMetadata } from '@/lib/seo/metadata';

export const metadata: Metadata = generateStaticMetadata(
  {
    fr: 'Rechercher des idées',
    en: 'Search Ideas',
  },
  {
    fr: 'Recherchez parmi les idées citoyennes pour améliorer Montréal. Filtrez par catégorie, score et date.',
    en: 'Search citizen ideas to improve Montreal. Filter by category, score, and date.',
  },
  'fr',
  '/search'
);

export default function SearchLayout({ children }: { children: React.ReactNode }) {
  return children;
}
