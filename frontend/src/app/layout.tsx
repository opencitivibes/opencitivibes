import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Providers from './providers';
import { getBaseMetadata, getSiteConfig } from '@/lib/seo/metadata';
import { StructuredData } from '@/components/seo/StructuredData';
import { DynamicLang } from '@/components/seo/DynamicLang';
import {
  generateWebSiteSchema,
  generateOrganizationSchema,
  combineSchemas,
} from '@/lib/seo/structured-data';
import { CookieNotice } from '@/components/CookieNotice';

// Optimized font configuration for Core Web Vitals
const inter = Inter({
  subsets: ['latin'],
  display: 'swap', // Prevents FOIT, minimizes CLS
  preload: true,
  fallback: [
    '-apple-system',
    'BlinkMacSystemFont',
    'Segoe UI',
    'Roboto',
    'Oxygen',
    'Ubuntu',
    'sans-serif',
  ],
  // Variable font for better performance
  variable: '--font-inter',
  // Adjust font fallback to minimize CLS
  adjustFontFallback: true,
});

// Get site config for metadata
const siteConfig = getSiteConfig();

// Enhanced metadata with language alternates
export const metadata: Metadata = {
  ...getBaseMetadata('fr'),
  manifest: '/manifest.json',
  alternates: {
    canonical: siteConfig.url,
    languages: {
      'fr-CA': siteConfig.url,
      'en-CA': siteConfig.url,
      'x-default': siteConfig.url,
    },
  },
};

// Viewport configuration
export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#0066CC' },
    { media: '(prefers-color-scheme: dark)', color: '#003366' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

// Global structured data for WebSite and Organization
const globalSchemas = combineSchemas(generateWebSiteSchema(), generateOrganizationSchema());

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const defaultLocale = process.env.NEXT_PUBLIC_DEFAULT_LOCALE || 'fr';

  return (
    <html lang={`${defaultLocale}-CA`} className={inter.variable} suppressHydrationWarning>
      <head>
        {/* Preconnect to critical origins for faster requests */}
        <link rel="preconnect" href={apiUrl} />
        <link rel="dns-prefetch" href={apiUrl} />

        {/* Preload critical hero image for LCP optimization */}
        <link rel="preload" href="/instance/hero.png" as="image" type="image/png" />

        <StructuredData data={globalSchemas} />

        {/* Cloudflare Web Analytics */}
        <script
          defer
          src="https://static.cloudflareinsights.com/beacon.min.js"
          data-cf-beacon='{"token": "284d8dbeefde4c64b4d839e6eefc6903"}'
        />
      </head>
      <body className={`${inter.className} theme-loading`}>
        {/* Fallback for no-JS: show content anyway */}
        <noscript>
          <style>{`body { opacity: 1 !important; }`}</style>
        </noscript>
        <DynamicLang />
        <Providers>
          {children}
          <CookieNotice />
        </Providers>
      </body>
    </html>
  );
}
