/**
 * Extended branding configuration for platform theming.
 */
export interface BrandingConfig {
  // Core colors
  primary_color: string;
  secondary_color: string;

  // Extended colors
  primary_dark?: string;
  accent?: string;
  success?: string;
  warning?: string;
  error?: string;

  // Dark mode
  dark_mode?: DarkModeConfig;

  // Typography
  fonts?: FontConfig;
  font_url?: string;

  // Border radius
  border_radius?: BorderRadiusPreset;

  // Images
  hero_image?: string;
  logo?: string;
  logo_dark?: string;
  favicon?: string;
  og_image?: string;
}

export interface DarkModeConfig {
  primary?: string;
  secondary?: string;
  background?: string;
  surface?: string;
  [key: string]: string | undefined;
}

export interface FontConfig {
  heading?: string;
  body?: string;
}

export type BorderRadiusPreset = 'none' | 'sm' | 'md' | 'lg' | 'full';
