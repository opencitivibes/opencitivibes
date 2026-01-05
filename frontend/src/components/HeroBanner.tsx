'use client';

import Link from 'next/link';
import { HeroImage } from './HeroImage';
import { useConfigTranslation } from '@/hooks/useConfigTranslation';
import { usePlatformConfig } from '@/lib/config/PlatformConfigProvider';

interface HeroBannerProps {
  /** Show the CTA buttons (Submit/Explore) */
  showButtons?: boolean;
}

export function HeroBanner({ showButtons = true }: HeroBannerProps) {
  const { t, instanceName, entityName, getLocalizedValue } = useConfigTranslation();
  const { location, config } = usePlatformConfig();

  // Check if hero overlay is enabled (default: true)
  const showOverlay = config?.branding?.hero_overlay !== false;

  // Use custom subtitle if provided, otherwise use default with entity name
  const customSubtitle = config?.branding?.hero_subtitle
    ? getLocalizedValue(config.branding.hero_subtitle)
    : null;
  const subtitle = customSubtitle || t('app.subtitle').replace('{{config.entityName}}', entityName);

  return (
    <section className="relative min-h-[180px] sm:h-56 md:h-64 overflow-hidden">
      {/* Background Image */}
      <HeroImage />

      {/* Gradient Overlay - can be disabled via config */}
      {showOverlay && (
        <div className="absolute inset-0 bg-gradient-to-br from-primary-950/70 via-primary-900/50 to-primary-700/40" />
      )}

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center justify-center h-full text-center px-4 py-6 sm:py-8 animate-hero-fade-in">
        <h1
          className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-extrabold text-white tracking-tight drop-shadow-xl mb-2 sm:mb-3"
          suppressHydrationWarning
        >
          {instanceName}
        </h1>
        <p
          className="text-sm sm:text-lg md:text-xl text-white/90 max-w-2xl mx-auto mb-1 sm:mb-2"
          suppressHydrationWarning
        >
          {subtitle}
        </p>

        {/* Location Indicator */}
        {location && (
          <div
            className={`flex items-center gap-1.5 sm:gap-2 text-white/80 ${showButtons ? 'mb-4 sm:mb-6' : ''}`}
          >
            <svg
              className="w-4 h-4 sm:w-5 sm:h-5"
              fill="currentColor"
              viewBox="0 0 20 20"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z"
                clipRule="evenodd"
              />
            </svg>
            <span className="text-xs sm:text-sm">{location}</span>
          </div>
        )}

        {/* CTA Buttons */}
        {showButtons && (
          <div className="flex flex-row items-center gap-2 sm:gap-3">
            <Link
              href="/submit"
              className="inline-flex items-center justify-center px-4 sm:px-6 py-2 sm:py-3 bg-white text-primary-700 text-sm sm:text-base font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 hover:-translate-y-0.5 focus:outline-none focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-primary-600"
            >
              {t('hero.submitIdeaShort', 'Proposer')}
            </Link>
            <Link
              href="/search"
              className="inline-flex items-center justify-center px-4 sm:px-6 py-2 sm:py-3 border-2 border-white/80 text-white text-sm sm:text-base font-semibold rounded-lg hover:bg-white/10 transition-all duration-200 focus:outline-none focus:border-white"
            >
              {t('hero.exploreIdeasShort', 'Explorer')}
            </Link>
          </div>
        )}
      </div>
    </section>
  );
}
