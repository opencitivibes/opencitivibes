'use client';

import Image from 'next/image';
import { usePlatformConfig } from '@/lib/config/PlatformConfigProvider';
import { useConfigTranslation } from '@/hooks/useConfigTranslation';

interface HeroImageProps {
  className?: string;
  priority?: boolean;
}

/**
 * Dynamic hero image component that uses platform configuration.
 * Falls back to default banner if no custom hero image is configured.
 */
export function HeroImage({ className = '', priority = true }: HeroImageProps) {
  const { config } = usePlatformConfig();
  const { t, entityName } = useConfigTranslation();

  const defaultHeroImage = process.env.NEXT_PUBLIC_DEFAULT_HERO_IMAGE || '/images/banner.png';
  const heroSrc = config?.branding?.hero_image || defaultHeroImage;
  const heroPosition = config?.branding?.hero_position || 'center';
  // Build alt text with entity name
  const altText = t('hero.imageAlt', 'City skyline').replace('{{config.entityName}}', entityName);

  return (
    <Image
      src={heroSrc}
      alt={altText}
      fill
      priority={priority}
      className={`object-cover ${className}`}
      style={{ objectPosition: heroPosition }}
      sizes="100vw"
    />
  );
}
