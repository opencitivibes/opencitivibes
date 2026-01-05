'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

export interface PlatformConfig {
  platform: {
    name: string;
    version?: string;
  };
  instance: {
    name: Record<string, string>;
    entity: {
      type: 'city' | 'region' | 'country' | 'organization' | 'community';
      name: Record<string, string>;
    };
    location?: {
      display: Record<string, string>;
      timezone?: string;
    };
  };
  branding?: {
    // Core colors (existing)
    primary_color: string;
    secondary_color: string;

    // Extended colors (new)
    primary_dark?: string;
    accent?: string;
    success?: string;
    warning?: string;
    error?: string;

    // Dark mode overrides (new)
    dark_mode?: {
      primary?: string;
      secondary?: string;
      background?: string;
      surface?: string;
      [key: string]: string | undefined;
    };

    // Typography (new)
    fonts?: {
      heading?: string;
      body?: string;
    };
    font_url?: string;

    // Border radius (new)
    border_radius?: 'none' | 'sm' | 'md' | 'lg' | 'full';

    // Images (existing + new)
    hero_image?: string;
    logo?: string;
    logo_dark?: string;
    favicon?: string;
    og_image?: string;

    // Hero customization
    hero_overlay?: boolean; // Show gradient overlay on hero (default: true)
    hero_subtitle?: Record<string, string>; // Custom subtitle (overrides default)
    hero_position?: string; // CSS object-position (e.g., "top", "center 30%", "bottom")
  };
  localization: {
    default_locale: string;
    supported_locales: string[];
    date_format?: Record<string, string>;
  };
  features: Record<string, boolean>;
  contact: {
    email: string;
  };
  legal?: {
    jurisdiction: Record<string, string>;
  };
}

interface PlatformConfigContextType {
  config: PlatformConfig | null;
  loading: boolean;
  error: Error | null;
  getLocalizedValue: (obj: Record<string, string> | undefined, fallback?: string) => string;
  instanceName: string;
  entityName: string;
  location: string;
}

const PlatformConfigContext = createContext<PlatformConfigContextType | null>(null);

function getFallbackConfig(): PlatformConfig {
  // Use environment variables for fallback values
  const instanceName = process.env.NEXT_PUBLIC_INSTANCE_NAME || 'OpenCitiVibes';
  const entityName = process.env.NEXT_PUBLIC_ENTITY_NAME || '';

  return {
    platform: { name: 'OpenCitiVibes' },
    instance: {
      name: { en: instanceName, fr: instanceName },
      entity: {
        type: 'city',
        name: { en: entityName, fr: entityName },
      },
      location: {
        display: { en: '', fr: '' },
      },
    },
    localization: {
      default_locale: process.env.NEXT_PUBLIC_DEFAULT_LOCALE || 'fr',
      supported_locales: ['fr', 'en'],
    },
    features: {},
    contact: { email: 'contact@opencitivibes.local' },
  };
}

export function PlatformConfigProvider({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation();
  // Initialize with fallback config to prevent SSR hydration issues
  const [config, setConfig] = useState<PlatformConfig | null>(getFallbackConfig);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function loadConfig() {
      try {
        // Determine API URL at runtime for mobile testing support
        let apiUrl: string;
        if (typeof window === 'undefined') {
          apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
        } else {
          const { protocol, hostname } = window.location;
          // If accessing via localhost, use localhost for API
          if (hostname === 'localhost' || hostname === '127.0.0.1') {
            apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
          } else {
            // Otherwise, use the same hostname with backend port (mobile/network access)
            apiUrl = `${protocol}//${hostname}:8000/api`;
          }
        }

        // Debug logging for mobile testing
        console.log('[PlatformConfig] Fetching from:', `${apiUrl}/config/public`);
        console.log(
          '[PlatformConfig] Window location:',
          typeof window !== 'undefined' ? window.location.href : 'SSR'
        );

        const response = await fetch(`${apiUrl}/config/public`);

        if (!response.ok) {
          throw new Error('Failed to load configuration');
        }

        const data = await response.json();
        setConfig(data);
      } catch (err) {
        // Enhanced error logging for debugging
        console.error('[PlatformConfig] Failed to load:', err);
        if (err instanceof TypeError && err.message.includes('fetch')) {
          console.error('[PlatformConfig] Network error - check if backend is reachable');
        }
        setError(err instanceof Error ? err : new Error('Unknown error'));
        // Use fallback config
        setConfig(getFallbackConfig());
      } finally {
        setLoading(false);
      }
    }

    loadConfig();
  }, []);

  const getLocalizedValue = (obj: Record<string, string> | undefined, fallback = ''): string => {
    if (!obj) return fallback;
    const keys = Object.keys(obj);
    const firstKey = keys.length > 0 ? keys[0] : undefined;
    return obj[i18n.language] || obj['en'] || (firstKey ? obj[firstKey] : undefined) || fallback;
  };

  const instanceName = config
    ? getLocalizedValue(config.instance.name, 'OpenCitiVibes')
    : 'OpenCitiVibes';

  const entityName = config ? getLocalizedValue(config.instance.entity.name, '') : '';

  const location = config?.instance.location
    ? getLocalizedValue(config.instance.location.display, '')
    : '';

  return (
    <PlatformConfigContext.Provider
      value={{
        config,
        loading,
        error,
        getLocalizedValue,
        instanceName,
        entityName,
        location,
      }}
    >
      {children}
    </PlatformConfigContext.Provider>
  );
}

export function usePlatformConfig() {
  const context = useContext(PlatformConfigContext);
  if (!context) {
    throw new Error('usePlatformConfig must be used within PlatformConfigProvider');
  }
  return context;
}
