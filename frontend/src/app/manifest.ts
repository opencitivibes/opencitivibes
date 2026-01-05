import { MetadataRoute } from 'next';

/**
 * Dynamic Web App Manifest.
 * Uses environment variables for instance-specific configuration.
 */
export default function manifest(): MetadataRoute.Manifest {
  const name = process.env.NEXT_PUBLIC_INSTANCE_NAME || 'OpenCitiVibes';
  const shortName = process.env.NEXT_PUBLIC_INSTANCE_SHORT_NAME || 'OCV';
  const description = process.env.NEXT_PUBLIC_TAGLINE || 'Citizen platform for sharing ideas';
  const themeColor = process.env.NEXT_PUBLIC_THEME_COLOR || '#0066CC';

  return {
    name,
    short_name: shortName,
    description,
    start_url: '/',
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: themeColor,
    icons: [
      {
        src: '/icons/icon-192x192.png',
        sizes: '192x192',
        type: 'image/png',
      },
      {
        src: '/icons/icon-512x512.png',
        sizes: '512x512',
        type: 'image/png',
      },
    ],
  };
}
