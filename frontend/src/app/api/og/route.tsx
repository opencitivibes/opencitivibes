import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

import { OG_WIDTH, OG_HEIGHT, OG_COLORS, OG_PADDING } from '@/lib/seo/og-constants';

export const runtime = 'edge';

export async function GET(request: NextRequest) {
  const instanceName = process.env.NEXT_PUBLIC_INSTANCE_NAME || 'OpenCitiVibes';
  const tagline = process.env.NEXT_PUBLIC_TAGLINE || 'Share your ideas';
  const locale = request.nextUrl.searchParams.get('locale') || 'fr';

  // Localized taglines
  const taglines: Record<string, string> = {
    fr: process.env.NEXT_PUBLIC_TAGLINE_FR || 'Partagez vos idées',
    en: process.env.NEXT_PUBLIC_TAGLINE_EN || tagline,
  };

  const displayTagline = taglines[locale] || taglines.fr;

  return new ImageResponse(
    <div
      style={{
        background: `linear-gradient(135deg, ${OG_COLORS.backgroundStart} 0%, ${OG_COLORS.backgroundMid} 50%, ${OG_COLORS.backgroundEnd} 100%)`,
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: OG_PADDING,
      }}
    >
      {/* Main title */}
      <div
        style={{
          fontSize: 72,
          fontWeight: 700,
          color: OG_COLORS.textPrimary,
          marginBottom: 24,
          textAlign: 'center',
        }}
      >
        {instanceName}
      </div>

      {/* Tagline */}
      <div
        style={{
          fontSize: 36,
          fontWeight: 400,
          color: OG_COLORS.textSecondary,
          textAlign: 'center',
          maxWidth: '80%',
        }}
      >
        {displayTagline}
      </div>

      {/* Decorative element */}
      <div
        style={{
          display: 'flex',
          marginTop: 48,
          gap: 12,
        }}
      >
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            style={{
              width: 8,
              height: 8,
              borderRadius: 4,
              backgroundColor: OG_COLORS.accent,
              opacity: 1 - (i - 1) * 0.25,
            }}
          />
        ))}
      </div>
    </div>,
    {
      width: OG_WIDTH,
      height: OG_HEIGHT,
    }
  );
}
