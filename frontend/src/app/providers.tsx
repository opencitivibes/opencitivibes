'use client';

import { useEffect, type ReactNode } from 'react';
import { I18nextProvider } from 'react-i18next';
import i18n from '@/i18n/config';
import Navbar from '@/components/Navbar';
import CollapsibleFooter from '@/components/CollapsibleFooter';
import LoadingBar from '@/components/LoadingBar';
import ScrollToTop from '@/components/ScrollToTop';
import { BetaAccessGate } from '@/components/BetaAccessGate';
import { useAuthStore } from '@/store/authStore';
import { Toaster } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { PlatformConfigProvider, usePlatformConfig } from '@/lib/config/PlatformConfigProvider';
import { initializeTheme, markThemeInitialized } from '@/lib/theme/themeConfig';
import { initializeSiteConfig } from '@/lib/seo/metadata';
import { DynamicHead } from '@/components/DynamicHead';
import { CommandPalette } from '@/components/CommandPalette';

/**
 * Initializes theme and SEO config from platform configuration.
 */
function ConfigInitializer({ children }: { children: ReactNode }) {
  const { config, loading } = usePlatformConfig();

  useEffect(() => {
    // Wait until config is loaded from API (loading becomes false)
    if (loading) return;

    if (config) {
      // Initialize theme from branding config
      if (config.branding) {
        initializeTheme(config.branding);
      } else {
        // No branding config - still reveal content with defaults
        markThemeInitialized();
      }

      // Initialize SEO metadata from config
      initializeSiteConfig({
        instance: config.instance,
        localization: config.localization,
        social: undefined, // Add social config when available in PlatformConfig
      });
    } else {
      // No config at all (unlikely) - reveal with defaults
      markThemeInitialized();
    }
  }, [config, loading]);

  return (
    <>
      <DynamicHead />
      {children}
    </>
  );
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const fetchUser = useAuthStore((state) => state.fetchUser);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  return (
    <I18nextProvider i18n={i18n}>
      <PlatformConfigProvider>
        <ConfigInitializer>
          <BetaAccessGate>
            <TooltipProvider delayDuration={300}>
              <LoadingBar />
              <div className="min-h-screen flex flex-col">
                <Navbar />
                <main className="flex-1">{children}</main>
                <CollapsibleFooter />
              </div>
              <ScrollToTop />
              <CommandPalette />
              <Toaster position="top-right" expand={false} richColors closeButton duration={4000} />
            </TooltipProvider>
          </BetaAccessGate>
        </ConfigInitializer>
      </PlatformConfigProvider>
    </I18nextProvider>
  );
}
