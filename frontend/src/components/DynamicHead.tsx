'use client';

import { useEffect } from 'react';
import { usePlatformConfig } from '@/lib/config/PlatformConfigProvider';

/**
 * Dynamic head component that updates document metadata based on platform configuration.
 * Currently supports dynamic favicon customization.
 */
export function DynamicHead() {
  const { config } = usePlatformConfig();

  useEffect(() => {
    if (config?.branding?.favicon) {
      // Update favicon dynamically
      const existingLink = document.querySelector("link[rel='icon']") as HTMLLinkElement | null;
      if (existingLink) {
        existingLink.href = config.branding.favicon;
      } else {
        // Create new favicon link if none exists
        const link = document.createElement('link');
        link.rel = 'icon';
        link.href = config.branding.favicon;
        document.head.appendChild(link);
      }
    }
  }, [config?.branding?.favicon]);

  return null;
}

export default DynamicHead;
