import { ImageResponse } from 'next/og';
import { NextRequest } from 'next/server';

import {
  OG_WIDTH,
  OG_HEIGHT,
  OG_COLORS,
  OG_FONTS,
  OG_TEXT,
  OG_PADDING,
  truncateText,
  formatScore,
  getScoreColor,
} from '@/lib/seo/og-constants';

export const runtime = 'edge';

// Revalidate every hour
export const revalidate = 3600;

// Use internal URL for server-side rendering (Docker service name), fallback to public URL
const API_BASE_URL =
  process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

interface IdeaData {
  id: number;
  title: string;
  score: number;
  author_display_name: string;
  category_name_en: string;
  category_name_fr: string;
}

async function fetchIdea(id: string): Promise<IdeaData | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/ideas/${id}`, {
      next: { revalidate: 3600 },
    });

    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const instanceName = process.env.NEXT_PUBLIC_INSTANCE_NAME || 'OpenCitiVibes';
  const locale = request.nextUrl.searchParams.get('locale') || 'fr';

  const idea = await fetchIdea(id);

  // If idea not found, return a default "idea not found" image
  if (!idea) {
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
        <div
          style={{
            fontSize: 48,
            fontWeight: 700,
            color: OG_COLORS.textPrimary,
            marginBottom: 24,
          }}
        >
          {instanceName}
        </div>
        <div
          style={{
            fontSize: 24,
            color: OG_COLORS.textMuted,
          }}
        >
          {locale === 'fr' ? "Cette idée n'existe plus" : 'This idea no longer exists'}
        </div>
      </div>,
      {
        width: OG_WIDTH,
        height: OG_HEIGHT,
      }
    );
  }

  const categoryName = locale === 'en' ? idea.category_name_en : idea.category_name_fr;
  const title = truncateText(idea.title, OG_TEXT.maxTitleLength);
  const authorName = truncateText(idea.author_display_name, OG_TEXT.maxAuthorLength);
  const scoreColor = getScoreColor(idea.score);
  const scoreText = formatScore(idea.score);
  const proposedByLabel = locale === 'fr' ? 'Proposé par' : 'Proposed by';
  const scoreLabel = 'Score';

  return new ImageResponse(
    <div
      style={{
        background: `linear-gradient(135deg, ${OG_COLORS.backgroundStart} 0%, ${OG_COLORS.backgroundMid} 50%, ${OG_COLORS.backgroundEnd} 100%)`,
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        padding: OG_PADDING,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 32,
        }}
      >
        {/* Site name */}
        <div
          style={{
            fontSize: OG_FONTS.siteNameSize,
            fontWeight: OG_FONTS.siteNameWeight,
            color: OG_COLORS.textPrimary,
          }}
        >
          {instanceName}
        </div>

        {/* Score */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
          }}
        >
          <div
            style={{
              fontSize: OG_FONTS.labelSize,
              fontWeight: OG_FONTS.labelWeight,
              color: OG_COLORS.textMuted,
              marginBottom: 4,
            }}
          >
            {scoreLabel}
          </div>
          <div
            style={{
              fontSize: OG_FONTS.scoreSize,
              fontWeight: OG_FONTS.scoreWeight,
              color: scoreColor,
            }}
          >
            {scoreText}
          </div>
        </div>
      </div>

      {/* Content area */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          flex: 1,
          justifyContent: 'center',
        }}
      >
        {/* Title */}
        <div
          style={{
            fontSize: OG_FONTS.titleSize,
            fontWeight: OG_FONTS.titleWeight,
            color: OG_COLORS.textPrimary,
            lineHeight: OG_FONTS.titleLineHeight,
            marginBottom: 24,
          }}
        >
          {title}
        </div>

        {/* Category badge */}
        <div
          style={{
            display: 'flex',
          }}
        >
          <div
            style={{
              fontSize: OG_FONTS.badgeSize,
              fontWeight: OG_FONTS.badgeWeight,
              color: OG_COLORS.textSecondary,
              backgroundColor: OG_COLORS.badgeBackground,
              border: `1px solid ${OG_COLORS.badgeBorder}`,
              borderRadius: 20,
              padding: '8px 16px',
            }}
          >
            {categoryName}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          borderTop: `1px solid rgba(255, 255, 255, 0.2)`,
          paddingTop: 16,
        }}
      >
        {/* Author initial avatar */}
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 20,
            backgroundColor: OG_COLORS.badgeBackground,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginRight: 12,
          }}
        >
          <span
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: OG_COLORS.textPrimary,
            }}
          >
            {authorName.charAt(0).toUpperCase()}
          </span>
        </div>

        <div
          style={{
            fontSize: OG_FONTS.footerSize,
            fontWeight: OG_FONTS.footerWeight,
            color: OG_COLORS.textSecondary,
          }}
        >
          {proposedByLabel}: {authorName}
        </div>
      </div>
    </div>,
    {
      width: OG_WIDTH,
      height: OG_HEIGHT,
    }
  );
}
