/**
 * Theme configuration system.
 *
 * Allows runtime customization of colors, fonts, and visual elements
 * based on platform configuration.
 */

export interface ThemeConfig {
  colors: {
    primary: string;
    primaryDark: string;
    secondary: string;
    accent: string;
    success: string;
    warning: string;
    error: string;
  };
  darkColors?: {
    primary?: string;
    secondary?: string;
    background?: string;
    surface?: string;
  };
  fonts: {
    heading: string;
    body: string;
  };
  fontUrl?: string;
  images: {
    logo: string;
    logoDark?: string;
    hero: string;
    favicon?: string;
    ogImage?: string;
  };
  borderRadius: 'none' | 'sm' | 'md' | 'lg' | 'full';
}

const DEFAULT_THEME: ThemeConfig = {
  colors: {
    primary: '#a855f7', // Purple - matches existing brand
    primaryDark: '#7e22ce',
    secondary: '#1a1a2e',
    accent: '#14b8a6', // Teal
    success: '#22c55e', // Green
    warning: '#eab308', // Yellow
    error: '#ef4444', // Red
  },
  fonts: {
    heading: 'system-ui, sans-serif',
    body: 'system-ui, sans-serif',
  },
  images: {
    logo: '/static/images/logo_tr3.svg',
    hero: '/images/banner.png',
  },
  borderRadius: 'lg',
};

let currentTheme: ThemeConfig = DEFAULT_THEME;

/**
 * Extended branding configuration from platform config.
 */
interface ExtendedBranding {
  primary_color?: string;
  secondary_color?: string;
  primary_dark?: string;
  accent?: string;
  success?: string;
  warning?: string;
  error?: string;
  dark_mode?: {
    primary?: string;
    secondary?: string;
    background?: string;
    surface?: string;
  };
  fonts?: {
    heading?: string;
    body?: string;
  };
  font_url?: string;
  border_radius?: 'none' | 'sm' | 'md' | 'lg' | 'full';
  hero_image?: string;
  logo?: string;
  logo_dark?: string;
  favicon?: string;
  og_image?: string;
}

/**
 * Initialize theme from platform configuration.
 */
export function initializeTheme(branding?: ExtendedBranding): void {
  if (!branding) return;

  const primaryColor = branding.primary_color || DEFAULT_THEME.colors.primary;

  currentTheme = {
    ...DEFAULT_THEME,
    colors: {
      ...DEFAULT_THEME.colors,
      primary: primaryColor,
      primaryDark: branding.primary_dark || darkenColor(primaryColor),
      secondary: branding.secondary_color || DEFAULT_THEME.colors.secondary,
      accent: branding.accent || DEFAULT_THEME.colors.accent,
      success: branding.success || DEFAULT_THEME.colors.success,
      warning: branding.warning || DEFAULT_THEME.colors.warning,
      error: branding.error || DEFAULT_THEME.colors.error,
    },
    darkColors: branding.dark_mode
      ? {
          primary: branding.dark_mode.primary,
          secondary: branding.dark_mode.secondary,
          background: branding.dark_mode.background,
          surface: branding.dark_mode.surface,
        }
      : undefined,
    fonts: {
      heading: branding.fonts?.heading || DEFAULT_THEME.fonts.heading,
      body: branding.fonts?.body || DEFAULT_THEME.fonts.body,
    },
    fontUrl: branding.font_url,
    images: {
      ...DEFAULT_THEME.images,
      logo: branding.logo || DEFAULT_THEME.images.logo,
      logoDark: branding.logo_dark,
      hero: branding.hero_image || DEFAULT_THEME.images.hero,
      favicon: branding.favicon,
      ogImage: branding.og_image,
    },
    borderRadius: branding.border_radius || DEFAULT_THEME.borderRadius,
  };

  // Apply CSS custom properties
  applyThemeToCss(currentTheme);
  // Load custom fonts if URL provided
  loadCustomFonts(currentTheme);
  // Mark theme as initialized to prevent FOIC
  markThemeInitialized();
}

/**
 * Mark theme as initialized to reveal content.
 * Removes 'theme-loading' and adds 'theme-initialized' class to body.
 */
export function markThemeInitialized(): void {
  if (typeof document === 'undefined') return;
  document.body.classList.remove('theme-loading');
  document.body.classList.add('theme-initialized');
}

/**
 * Border radius presets mapping.
 */
const RADIUS_PRESETS = {
  none: '0',
  sm: '0.25rem',
  md: '0.5rem',
  lg: '0.75rem',
  full: '9999px',
} as const;

/**
 * Convert hex color to RGB values.
 */
function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!result || !result[1] || !result[2] || !result[3]) {
    return null;
  }
  return {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16),
  };
}

/**
 * Darken a hex color by a percentage.
 */
function darkenColor(hex: string, percent: number = 20): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;

  const factor = 1 - percent / 100;
  const r = Math.round(rgb.r * factor);
  const g = Math.round(rgb.g * factor);
  const b = Math.round(rgb.b * factor);

  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

/**
 * Lighten a hex color by a percentage.
 */
function lightenColor(hex: string, percent: number): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;

  const r = Math.round(rgb.r + (255 - rgb.r) * (percent / 100));
  const g = Math.round(rgb.g + (255 - rgb.g) * (percent / 100));
  const b = Math.round(rgb.b + (255 - rgb.b) * (percent / 100));

  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
}

/**
 * Generate a full color scale from a base color.
 * Returns shades from 50 (lightest) to 950 (darkest).
 */
function generateColorScale(baseColor: string): Record<string, string> {
  return {
    '50': lightenColor(baseColor, 95),
    '100': lightenColor(baseColor, 90),
    '200': lightenColor(baseColor, 75),
    '300': lightenColor(baseColor, 55),
    '400': lightenColor(baseColor, 30),
    '500': baseColor,
    '600': darkenColor(baseColor, 10),
    '700': darkenColor(baseColor, 25),
    '800': darkenColor(baseColor, 40),
    '900': darkenColor(baseColor, 55),
    '950': darkenColor(baseColor, 70),
  };
}

/**
 * Convert hex color to HSL values for shadcn/ui compatibility.
 */
function hexToHsl(hex: string): { h: number; s: number; l: number } | null {
  const rgb = hexToRgb(hex);
  if (!rgb) return null;

  const r = rgb.r / 255;
  const g = rgb.g / 255;
  const b = rgb.b / 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let h = 0;
  let s = 0;
  const l = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);

    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      case b:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }

  return {
    h: Math.round(h * 360),
    s: Math.round(s * 100),
    l: Math.round(l * 100),
  };
}

/**
 * Apply theme to CSS custom properties.
 */
function applyThemeToCss(theme: ThemeConfig): void {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;

  // Apply all color variables
  const colorMapping: Record<string, string> = {
    primary: theme.colors.primary,
    'primary-dark': theme.colors.primaryDark,
    secondary: theme.colors.secondary,
    accent: theme.colors.accent,
    success: theme.colors.success,
    warning: theme.colors.warning,
    error: theme.colors.error,
  };

  Object.entries(colorMapping).forEach(([name, color]) => {
    const rgb = hexToRgb(color);
    const hsl = hexToHsl(color);

    root.style.setProperty(`--color-theme-${name}`, color);

    if (rgb) {
      root.style.setProperty(`--color-theme-${name}-rgb`, `${rgb.r} ${rgb.g} ${rgb.b}`);
    }

    // Set HSL for shadcn/ui compatibility (primary only)
    if (name === 'primary' && hsl) {
      root.style.setProperty('--primary', `${hsl.h} ${hsl.s}% ${hsl.l}%`);
      root.style.setProperty('--ring', `${hsl.h} ${hsl.s}% ${hsl.l}%`);

      // Also set dark mode HSL values (lighter version for visibility)
      const darkPrimaryLightness = Math.min(hsl.l + 10, 80); // Slightly lighter for dark mode
      root.style.setProperty('--primary-dark-hsl', `${hsl.h} ${hsl.s}% ${darkPrimaryLightness}%`);

      // Set accent for dark mode (even lighter)
      const accentLightness = Math.min(hsl.l - 25, 35);
      root.style.setProperty('--accent-dark-hsl', `${hsl.h} ${hsl.s}% ${accentLightness}%`);
    }
  });

  // Generate and apply full primary color scale for Tailwind classes
  const primaryScale = generateColorScale(theme.colors.primary);
  Object.entries(primaryScale).forEach(([shade, color]) => {
    root.style.setProperty(`--color-primary-${shade}`, color);
    // Also set RGB version for opacity support (space-separated for Tailwind)
    const rgb = hexToRgb(color);
    if (rgb) {
      root.style.setProperty(`--color-primary-${shade}-rgb`, `${rgb.r} ${rgb.g} ${rgb.b}`);
    }
  });

  // Also generate accent color scale
  const accentScale = generateColorScale(theme.colors.accent);
  Object.entries(accentScale).forEach(([shade, color]) => {
    root.style.setProperty(`--color-accent-${shade}`, color);
    // Also set RGB version for opacity support (space-separated for Tailwind)
    const rgb = hexToRgb(color);
    if (rgb) {
      root.style.setProperty(`--color-accent-${shade}-rgb`, `${rgb.r} ${rgb.g} ${rgb.b}`);
    }
  });

  // Update shadow colors to use theme primary
  const primaryRgb = hexToRgb(theme.colors.primary);
  if (primaryRgb) {
    root.style.setProperty(
      '--shadow-purple-md',
      `0 4px 6px -1px rgba(${primaryRgb.r}, ${primaryRgb.g}, ${primaryRgb.b}, 0.2), 0 2px 4px -2px rgba(${primaryRgb.r}, ${primaryRgb.g}, ${primaryRgb.b}, 0.2)`
    );
    root.style.setProperty(
      '--shadow-purple-lg',
      `0 10px 15px -3px rgba(${primaryRgb.r}, ${primaryRgb.g}, ${primaryRgb.b}, 0.2), 0 4px 6px -4px rgba(${primaryRgb.r}, ${primaryRgb.g}, ${primaryRgb.b}, 0.2)`
    );
  }

  // Apply dark mode override variables
  if (theme.darkColors) {
    Object.entries(theme.darkColors).forEach(([name, color]) => {
      if (color) {
        const rgb = hexToRgb(color);
        root.style.setProperty(`--color-theme-dark-${name}`, color);
        if (rgb) {
          root.style.setProperty(`--color-theme-dark-${name}-rgb`, `${rgb.r} ${rgb.g} ${rgb.b}`);
        }
      }
    });
  }

  // Apply border radius
  const radiusValue: string = RADIUS_PRESETS[theme.borderRadius] ?? RADIUS_PRESETS.lg;
  root.style.setProperty('--radius', radiusValue);
  root.style.setProperty('--radius-lg', radiusValue);
  root.style.setProperty('--radius-md', `calc(${radiusValue} - 2px)`);
  root.style.setProperty('--radius-sm', `calc(${radiusValue} - 4px)`);

  // Apply font families
  root.style.setProperty('--font-heading', `'${theme.fonts.heading}', system-ui, sans-serif`);
  root.style.setProperty('--font-body', `'${theme.fonts.body}', system-ui, sans-serif`);
}

/**
 * Load custom fonts from Google Fonts or other CDN.
 */
function loadCustomFonts(theme: ThemeConfig): void {
  if (!theme.fontUrl || typeof document === 'undefined') return;

  // Check if font link already exists
  const existingLink = document.querySelector(`link[href="${theme.fontUrl}"]`);
  if (existingLink) return;

  // Add preconnect for Google Fonts
  if (theme.fontUrl.includes('fonts.googleapis.com')) {
    const preconnectGoogle = document.createElement('link');
    preconnectGoogle.rel = 'preconnect';
    preconnectGoogle.href = 'https://fonts.googleapis.com';
    document.head.appendChild(preconnectGoogle);

    const preconnectGstatic = document.createElement('link');
    preconnectGstatic.rel = 'preconnect';
    preconnectGstatic.href = 'https://fonts.gstatic.com';
    preconnectGstatic.crossOrigin = 'anonymous';
    document.head.appendChild(preconnectGstatic);
  }

  // Add font stylesheet
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  link.href = theme.fontUrl;
  link.setAttribute('data-theme-font', 'true');
  document.head.appendChild(link);
}

/**
 * Get current theme configuration.
 */
export function getTheme(): ThemeConfig {
  return currentTheme;
}

/**
 * Get hero image URL from current theme.
 */
export function getHeroImage(): string {
  return currentTheme.images.hero || '/images/banner.png';
}

/**
 * Get logo URL from current theme.
 */
export function getLogo(): string {
  return currentTheme.images.logo || '/static/images/logo_tr3.svg';
}

/**
 * Get dark mode logo if available, otherwise regular logo.
 */
export function getLogoDark(): string | undefined {
  return currentTheme.images.logoDark;
}

/**
 * Get favicon URL from current theme.
 */
export function getFavicon(): string | undefined {
  return currentTheme.images.favicon;
}

/**
 * Get Open Graph image URL from current theme.
 */
export function getOgImage(): string | undefined {
  return currentTheme.images.ogImage;
}

/**
 * Get current border radius preset.
 */
export function getBorderRadius(): string {
  return currentTheme.borderRadius;
}
