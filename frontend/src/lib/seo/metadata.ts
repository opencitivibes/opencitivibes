import { Metadata } from 'next';

import { OG_WIDTH, OG_HEIGHT } from './og-constants';

/**
 * Site configuration interface for SEO metadata.
 * All instance-specific values are pulled from platform configuration.
 */
export interface SiteConfig {
  name: Record<string, string>;
  description: Record<string, string>;
  url: string;
  locale: {
    default: string;
    alternate: string;
  };
  twitter?: {
    handle: string;
  };
  keywords?: Record<string, string[]>;
  images: {
    og: string;
    twitter: string;
    icon: string;
    appleTouchIcon: string;
  };
}

// Cache for site configuration populated from platform config
let siteConfigCache: SiteConfig | null = null;

/**
 * Initialize site config from platform configuration.
 * Called during app initialization from providers.tsx.
 */
export function initializeSiteConfig(config: {
  instance: {
    name: Record<string, string>;
    entity: {
      name: Record<string, string>;
    };
  };
  localization: {
    default_locale: string;
    supported_locales: string[];
  };
  social?: {
    twitter?: string;
  };
}): void {
  const defaultLocale = config.localization.default_locale;
  const alternateLocale =
    config.localization.supported_locales.find((l) => l !== defaultLocale) || 'en';

  siteConfigCache = {
    name: config.instance.name,
    description: generateDescriptions(config.instance.name, config.instance.entity.name),
    url: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
    locale: {
      default: `${defaultLocale}_CA`,
      alternate: `${alternateLocale}_CA`,
    },
    twitter: config.social?.twitter ? { handle: config.social.twitter } : undefined,
    keywords: generateKeywords(config.instance.entity.name),
    images: {
      og: '/opengraph-image',
      twitter: '/twitter-image',
      icon: '/icon',
      appleTouchIcon: '/apple-icon',
    },
  };
}

function generateDescriptions(
  instanceName: Record<string, string>,
  entityName: Record<string, string>
): Record<string, string> {
  return {
    fr: `Partagez vos idées pour améliorer la vie à ${entityName.fr || entityName.en}. Plateforme citoyenne pour proposer, discuter et voter sur des idées innovantes.`,
    en: `Share your ideas to improve life in ${entityName.en}. Citizen platform to submit, discuss, and vote on innovative ideas.`,
  };
}

function generateKeywords(entityName: Record<string, string>): Record<string, string[]> {
  const entityFr = entityName.fr ?? entityName.en ?? '';
  const entityEn = entityName.en ?? '';

  return {
    fr: [entityFr, 'idées', 'citoyens', 'participation', 'ville', 'amélioration'].filter(Boolean),
    en: [entityEn, 'ideas', 'citizens', 'participation', 'city', 'improvement'].filter(Boolean),
  };
}

/**
 * Get site configuration with fallback for SSR.
 * Uses cached config if available, otherwise returns defaults.
 */
export function getSiteConfig(): SiteConfig {
  if (siteConfigCache) return siteConfigCache;

  // Fallback for SSR before client-side hydration
  return {
    name: { en: 'Ideas for Montreal', fr: 'Idées pour Montréal' },
    description: {
      en: 'Share your ideas to improve life in Montreal. Citizen platform to submit, discuss, and vote on innovative ideas.',
      fr: 'Partagez vos idées pour améliorer la vie à Montréal. Plateforme citoyenne pour proposer, discuter et voter sur des idées innovantes.',
    },
    url: process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000',
    locale: { default: 'fr_CA', alternate: 'en_CA' },
    images: {
      og: '/opengraph-image',
      twitter: '/twitter-image',
      icon: '/icon',
      appleTouchIcon: '/apple-icon',
    },
  };
}

// Legacy export for backward compatibility
export const siteConfig = getSiteConfig();

// Base metadata shared across all pages
export function getBaseMetadata(locale: string = 'fr'): Metadata {
  const config = getSiteConfig();
  const siteName = config.name[locale] ?? config.name.en ?? 'OpenCitiVibes';
  const siteDescription =
    config.description[locale] ?? config.description.en ?? 'Citizen ideas platform';

  return {
    metadataBase: new URL(config.url),
    title: {
      default: siteName,
      template: `%s | ${siteName}`,
    },
    description: siteDescription,
    keywords: config.keywords?.[locale] ?? [],
    authors: [{ name: siteName }],
    creator: siteName,
    publisher: siteName,
    formatDetection: {
      email: false,
      address: false,
      telephone: false,
    },
    openGraph: {
      type: 'website',
      locale: config.locale.default,
      alternateLocale: config.locale.alternate,
      siteName: siteName,
      images: [
        {
          url: `/api/og?locale=${locale}`,
          width: OG_WIDTH,
          height: OG_HEIGHT,
          alt: siteName,
        },
      ],
    },
    twitter: config.twitter
      ? {
          card: 'summary_large_image',
          site: config.twitter.handle,
          creator: config.twitter.handle,
          images: [`/api/og?locale=${locale}`],
        }
      : {
          card: 'summary_large_image',
          images: [`/api/og?locale=${locale}`],
        },
    icons: {
      icon: config.images.icon,
      apple: config.images.appleTouchIcon,
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        'max-video-preview': -1,
        'max-image-preview': 'large',
        'max-snippet': -1,
      },
    },
  };
}

// Generate metadata for static pages
export function generateStaticMetadata(
  title: { fr: string; en: string; es?: string },
  description: { fr: string; en: string; es?: string },
  locale: string = 'fr',
  path?: string
): Metadata {
  const config = getSiteConfig();
  const base = getBaseMetadata(locale);
  const url = path ? `${config.url}${path}` : undefined;

  const titleValue = title[locale as keyof typeof title] || title.en;
  const descValue = description[locale as keyof typeof description] || description.en;

  return {
    ...base,
    title: titleValue,
    description: descValue,
    openGraph: {
      ...base.openGraph,
      title: titleValue,
      description: descValue,
      url,
    },
    twitter: {
      ...base.twitter,
      title: titleValue,
      description: descValue,
    },
    alternates: path
      ? {
          canonical: url,
          languages: {
            'fr-CA': url,
            'en-CA': url,
            'es-ES': url,
            'x-default': url,
          },
        }
      : undefined,
  };
}

// Utility: Strip HTML tags from description
export function stripHtml(html: string): string {
  return html
    .replace(/<[^>]*>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
}

// Generate metadata for idea pages
export function generateIdeaMetadata(
  idea: {
    id: number;
    title: string;
    description: string;
    author_display_name: string;
    category_name_fr?: string;
    category_name_en?: string;
    category_name_es?: string;
    created_at: string;
    score: number;
    upvotes: number;
    tags?: Array<{ display_name: string }>;
  },
  locale: string = 'fr'
): Metadata {
  const config = getSiteConfig();
  const base = getBaseMetadata(locale);
  const url = `${config.url}/ideas/${idea.id}`;

  // Dynamic OG image URL for this specific idea
  const ogImageUrl = `/api/og/ideas/${idea.id}?locale=${locale}`;

  // Truncate description for meta (max 160 chars)
  const plainDescription = stripHtml(idea.description);
  const truncatedDescription =
    plainDescription.length > 160 ? plainDescription.substring(0, 157) + '...' : plainDescription;

  // Get localized category name with fallback to English
  const categoryNameKey = `category_name_${locale}` as keyof typeof idea;
  const categoryName =
    (idea[categoryNameKey] as string | undefined) || idea.category_name_en || idea.category_name_fr;
  // Use first keyword from config for location-based keyword
  const locationKeyword = config.keywords?.[locale]?.[0] || '';
  const keywords = [
    locationKeyword,
    categoryName,
    ...(idea.tags?.map((t) => t.display_name) || []),
  ].filter((k): k is string => Boolean(k));

  return {
    ...base,
    title: idea.title,
    description: truncatedDescription,
    keywords,
    authors: [{ name: idea.author_display_name }],
    openGraph: {
      ...base.openGraph,
      type: 'article',
      title: idea.title,
      description: truncatedDescription,
      url,
      publishedTime: idea.created_at,
      authors: [idea.author_display_name],
      tags: keywords as string[],
      images: [
        {
          url: ogImageUrl,
          width: OG_WIDTH,
          height: OG_HEIGHT,
          alt: idea.title,
        },
      ],
    },
    twitter: {
      ...base.twitter,
      card: 'summary_large_image',
      title: idea.title,
      description: truncatedDescription,
      images: [ogImageUrl],
    },
    alternates: {
      canonical: url,
      languages: {
        'fr-CA': url,
        'en-CA': url,
        'x-default': url,
      },
    },
  };
}

// Generate metadata for tag pages
export function generateTagMetadata(
  tagName: string,
  ideaCount: number,
  locale: string = 'fr'
): Metadata {
  const config = getSiteConfig();
  const base = getBaseMetadata(locale);
  const url = `${config.url}/tags/${encodeURIComponent(tagName)}`;
  const siteName = config.name[locale] || config.name.en;

  const titleMap: Record<string, string> = {
    fr: `#${tagName} - Idées étiquetées`,
    en: `#${tagName} - Tagged Ideas`,
    es: `#${tagName} - Ideas etiquetadas`,
  };
  const title = titleMap[locale] || titleMap.en;

  const descriptionMap: Record<string, string> = {
    fr: `Explorez ${ideaCount} idée(s) étiquetée(s) avec #${tagName} sur ${siteName}.`,
    en: `Explore ${ideaCount} idea(s) tagged with #${tagName} on ${siteName}.`,
    es: `Explora ${ideaCount} idea(s) etiquetada(s) con #${tagName} en ${siteName}.`,
  };
  const description = descriptionMap[locale] || descriptionMap.en;

  return {
    ...base,
    title,
    description,
    openGraph: {
      ...base.openGraph,
      title,
      description,
      url,
    },
    twitter: {
      ...base.twitter,
      title,
      description,
    },
    alternates: {
      canonical: url,
      languages: {
        'fr-CA': url,
        'en-CA': url,
        'x-default': url,
      },
    },
  };
}

// Metadata for noindex pages (admin, auth)
export const noIndexMetadata: Metadata = {
  robots: {
    index: false,
    follow: false,
  },
};
