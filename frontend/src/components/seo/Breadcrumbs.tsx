'use client';

import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { ChevronRight, Home } from 'lucide-react';
import { siteConfig } from '@/lib/seo/metadata';

export interface BreadcrumbItem {
  label: string;
  href?: string;
  translationKey?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumbs({ items, className = '' }: BreadcrumbsProps) {
  const { t } = useTranslation();

  const schemaItems = [
    { name: t('nav.home', 'Accueil'), url: siteConfig.url },
    ...items.map((item) => ({
      name: item.translationKey ? t(item.translationKey, item.label) : item.label,
      url: item.href ? `${siteConfig.url}${item.href}` : '',
    })),
  ].filter((item) => item.url);

  return (
    <nav
      aria-label={t('common.breadcrumb', "Fil d'Ariane")}
      className={`flex items-center text-sm text-gray-500 ${className}`}
    >
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          // nosemgrep
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            itemListElement: schemaItems.map((item, index) => ({
              '@type': 'ListItem',
              position: index + 1,
              name: item.name,
              item: item.url,
            })),
          }),
        }}
      />

      <ol className="flex items-center space-x-1 flex-wrap">
        <li className="flex items-center">
          <Link
            href="/"
            className="hover:text-primary-600 transition-colors flex items-center"
            aria-label={t('nav.home', 'Accueil')}
          >
            <Home className="w-4 h-4" aria-hidden="true" />
          </Link>
        </li>

        {items.map((item, index) => {
          const label = item.translationKey ? t(item.translationKey, item.label) : item.label;
          const isLast = index === items.length - 1;

          return (
            <li key={index} className="flex items-center">
              <ChevronRight className="w-4 h-4 mx-1 text-gray-400" aria-hidden="true" />
              {item.href && !isLast ? (
                <Link href={item.href} className="hover:text-primary-600 transition-colors">
                  {label}
                </Link>
              ) : (
                <span
                  className={isLast ? 'text-gray-900 font-medium' : ''}
                  aria-current={isLast ? 'page' : undefined}
                >
                  {label}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
