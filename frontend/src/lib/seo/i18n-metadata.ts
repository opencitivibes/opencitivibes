import { Metadata } from 'next';
import { siteConfig, getBaseMetadata } from './metadata';

// Supported SEO locales (can be expanded)
export type SeoLocale = 'fr' | 'en' | 'es';

/**
 * Generate metadata with multiple language versions.
 * This helps search engines understand the multilingual nature of the content.
 */
export function generateBilingualMetadata(
  title: { fr: string; en: string; es?: string },
  description: { fr: string; en: string; es?: string },
  path: string,
  options?: {
    defaultLocale?: SeoLocale;
    openGraphType?: 'website' | 'article';
    noIndex?: boolean;
  }
): Metadata {
  const { defaultLocale = 'fr', openGraphType = 'website', noIndex = false } = options || {};

  const cleanPath = path === '/' ? '' : path.replace(/\/$/, '');
  const fullUrl = `${siteConfig.url}${cleanPath}`;

  const base = getBaseMetadata(defaultLocale);

  const getOpenGraphLocale = (locale: string): string => {
    switch (locale) {
      case 'fr':
        return 'fr_CA';
      case 'es':
        return 'es_ES';
      default:
        return 'en_CA';
    }
  };

  // Get alternate locales (all supported locales except the current one)
  const getAlternateLocales = (currentLocale: string): string[] => {
    const allLocales = ['fr_CA', 'en_CA', 'es_ES'];
    const currentOgLocale = getOpenGraphLocale(currentLocale);
    return allLocales.filter((l) => l !== currentOgLocale);
  };

  const titleValue = title[defaultLocale] || title.en;
  const descValue = description[defaultLocale] || description.en;

  return {
    ...base,
    title: titleValue,
    description: descValue,
    alternates: {
      canonical: fullUrl,
      languages: {
        'fr-CA': fullUrl,
        'en-CA': fullUrl,
        'es-ES': fullUrl,
        'x-default': fullUrl,
      },
    },
    openGraph: {
      ...base.openGraph,
      type: openGraphType,
      title: titleValue,
      description: descValue,
      url: fullUrl,
      locale: getOpenGraphLocale(defaultLocale),
      alternateLocale: getAlternateLocales(defaultLocale),
    },
    twitter: {
      ...base.twitter,
      title: titleValue,
      description: descValue,
    },
    robots: noIndex ? { index: false, follow: false } : base.robots,
  };
}

/**
 * Get locale-specific translations for common SEO terms.
 */
export const seoTranslations = {
  home: { fr: 'Accueil', en: 'Home', es: 'Inicio' },
  ideas: { fr: 'Idées', en: 'Ideas', es: 'Ideas' },
  tags: { fr: 'Étiquettes', en: 'Tags', es: 'Etiquetas' },
  search: { fr: 'Recherche', en: 'Search', es: 'Buscar' },
  privacy: {
    fr: 'Politique de confidentialité',
    en: 'Privacy Policy',
    es: 'Política de privacidad',
  },
  terms: { fr: "Conditions d'utilisation", en: 'Terms of Service', es: 'Términos de servicio' },
  contact: { fr: 'Contact', en: 'Contact', es: 'Contacto' },
  submit: { fr: 'Proposer une idée', en: 'Submit an Idea', es: 'Proponer una idea' },
  leaderboard: { fr: 'Classement', en: 'Leaderboard', es: 'Clasificación' },
  notFound: { fr: 'Page non trouvée', en: 'Page Not Found', es: 'Página no encontrada' },
} as const;

/**
 * Generate title with site name suffix.
 */
export function generateTitle(
  pageTitle: { fr: string; en: string; es?: string },
  locale: SeoLocale = 'fr',
  includeSiteName = true
): string {
  const title = pageTitle[locale] || pageTitle.en;
  const siteName = siteConfig.name[locale] || siteConfig.name.en;
  if (includeSiteName) {
    return `${title} | ${siteName}`;
  }
  return title;
}
