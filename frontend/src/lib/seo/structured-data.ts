import { siteConfig, stripHtml } from './metadata';
import { getSupportedIntlLocales } from '@/lib/i18n-helpers';

// Type definitions for JSON-LD
interface WithContext<T extends string> {
  '@context': 'https://schema.org';
  '@type': T;
  [key: string]: unknown;
}

/**
 * Get the Intl locale code for structured data.
 */
function getStructuredDataLocale(locale: string): string {
  switch (locale) {
    case 'fr':
      return 'fr-CA';
    case 'es':
      return 'es-ES';
    default:
      return 'en-CA';
  }
}

// WebSite schema - enables sitelinks search box
export function generateWebSiteSchema(): WithContext<'WebSite'> {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: siteConfig.name.fr,
    alternateName: siteConfig.name.en,
    url: siteConfig.url,
    potentialAction: {
      '@type': 'SearchAction',
      target: {
        '@type': 'EntryPoint',
        urlTemplate: `${siteConfig.url}/search?q={search_term_string}`,
      },
      'query-input': 'required name=search_term_string',
    },
    inLanguage: getSupportedIntlLocales(),
  };
}

// Organization schema - brand knowledge panel
export function generateOrganizationSchema(): WithContext<'Organization'> {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: siteConfig.name.fr,
    alternateName: siteConfig.name.en,
    url: siteConfig.url,
    logo: `${siteConfig.url}/logo.png`,
    description: siteConfig.description.fr,
    foundingLocation: {
      '@type': 'Place',
      name: 'Montreal, Quebec, Canada',
      address: {
        '@type': 'PostalAddress',
        addressLocality: 'Montreal',
        addressRegion: 'Quebec',
        addressCountry: 'CA',
      },
    },
    areaServed: {
      '@type': 'City',
      name: 'Montreal',
      containedInPlace: {
        '@type': 'AdministrativeArea',
        name: 'Quebec',
      },
    },
    sameAs: [
      // Social media URLs can be added here when available
    ],
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'customer service',
      url: `${siteConfig.url}/contact`,
      availableLanguage: ['French', 'English', 'Spanish'],
    },
  };
}

// Breadcrumb schema
export interface BreadcrumbItem {
  name: string;
  url: string;
}

export function generateBreadcrumbSchema(items: BreadcrumbItem[]): WithContext<'BreadcrumbList'> {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name: item.name,
      item: item.url,
    })),
  };
}

// Article/CreativeWork schema for ideas
export interface IdeaForSchema {
  id: number;
  title: string;
  description: string;
  author_display_name: string;
  category_name_fr?: string;
  category_name_en?: string;
  created_at: string;
  updated_at?: string;
  score: number;
  upvotes: number;
  downvotes: number;
  comment_count?: number;
  tags?: Array<{ display_name: string }>;
  status: string;
}

export function generateIdeaSchema(
  idea: IdeaForSchema,
  locale: string = 'fr'
): WithContext<'Article'> {
  const plainDescription = stripHtml(idea.description);
  const truncatedDescription =
    plainDescription.length > 200 ? plainDescription.substring(0, 197) + '...' : plainDescription;

  // Get localized category name with fallback
  const categoryNameKey = `category_name_${locale}` as keyof IdeaForSchema;
  const categoryName =
    (idea[categoryNameKey] as string | undefined) || idea.category_name_en || idea.category_name_fr;

  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    '@id': `${siteConfig.url}/ideas/${idea.id}`,
    headline: idea.title,
    description: truncatedDescription,
    articleBody: plainDescription,
    url: `${siteConfig.url}/ideas/${idea.id}`,
    datePublished: idea.created_at,
    dateModified: idea.updated_at || idea.created_at,
    author: {
      '@type': 'Person',
      name: idea.author_display_name,
    },
    publisher: {
      '@type': 'Organization',
      name: siteConfig.name[locale],
      url: siteConfig.url,
      logo: {
        '@type': 'ImageObject',
        url: `${siteConfig.url}/logo.png`,
      },
    },
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `${siteConfig.url}/ideas/${idea.id}`,
    },
    interactionStatistic: [
      {
        '@type': 'InteractionCounter',
        interactionType: 'https://schema.org/LikeAction',
        userInteractionCount: idea.upvotes,
      },
      {
        '@type': 'InteractionCounter',
        interactionType: 'https://schema.org/DislikeAction',
        userInteractionCount: idea.downvotes,
      },
      {
        '@type': 'InteractionCounter',
        interactionType: 'https://schema.org/CommentAction',
        userInteractionCount: idea.comment_count || 0,
      },
    ],
    keywords: [categoryName, ...(idea.tags?.map((t) => t.display_name) || [])].filter(
      (k): k is string => Boolean(k)
    ),
    inLanguage: getStructuredDataLocale(locale),
    about: {
      '@type': 'Thing',
      name: categoryName || 'Civic Ideas',
    },
    locationCreated: {
      '@type': 'City',
      name: 'Montreal',
    },
  };
}

// CollectionPage schema for tag pages and home
export function generateCollectionPageSchema(
  title: string,
  description: string,
  url: string,
  itemCount: number,
  locale: string = 'fr'
): WithContext<'CollectionPage'> {
  return {
    '@context': 'https://schema.org',
    '@type': 'CollectionPage',
    name: title,
    description: description,
    url: url,
    numberOfItems: itemCount,
    inLanguage: getStructuredDataLocale(locale),
    isPartOf: {
      '@type': 'WebSite',
      name: siteConfig.name[locale] || siteConfig.name.en,
      url: siteConfig.url,
    },
  };
}

// WebPage schema for static pages
export function generateWebPageSchema(
  title: string,
  description: string,
  url: string,
  pageType: 'AboutPage' | 'ContactPage' | 'FAQPage' | 'WebPage' = 'WebPage',
  locale: string = 'fr'
): WithContext<typeof pageType> {
  const siteName = siteConfig.name[locale] || siteConfig.name.en;
  return {
    '@context': 'https://schema.org',
    '@type': pageType,
    name: title,
    description: description,
    url: url,
    inLanguage: getStructuredDataLocale(locale),
    isPartOf: {
      '@type': 'WebSite',
      name: siteName,
      url: siteConfig.url,
    },
    publisher: {
      '@type': 'Organization',
      name: siteName,
      url: siteConfig.url,
    },
  };
}

// Serialize schema for use in <script> tag
export function serializeSchema<T>(schema: T): string {
  return JSON.stringify(schema, null, 0);
}

// JSON-LD schema base type
export type JsonLdSchema = {
  '@context': 'https://schema.org';
  '@type': string;
  [key: string]: unknown;
};

// Helper to create combined schema array
export function combineSchemas(...schemas: JsonLdSchema[]): JsonLdSchema[] {
  return schemas;
}
