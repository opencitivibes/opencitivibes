import { MetadataRoute } from 'next';

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://idees-montreal.ca';
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Static pages that don't change often
// Note: Only include pages that should be indexed (no noindex pages)
const staticPages = [
  { path: '/', priority: 1.0, changeFrequency: 'daily' as const },
  { path: '/search', priority: 0.8, changeFrequency: 'daily' as const },
  { path: '/privacy', priority: 0.2, changeFrequency: 'yearly' as const },
  { path: '/terms', priority: 0.2, changeFrequency: 'yearly' as const },
  { path: '/contact', priority: 0.4, changeFrequency: 'monthly' as const },
];

interface SitemapIdea {
  id: number;
  updated_at: string;
  score: number;
}

interface SitemapTag {
  name: string;
  idea_count: number;
}

// Fetch approved ideas for sitemap
async function getApprovedIdeas(): Promise<SitemapIdea[]> {
  try {
    // Fetch all approved ideas from leaderboard
    const response = await fetch(`${API_URL}/ideas/leaderboard?limit=1000`, {
      next: { revalidate: 3600 }, // Revalidate every hour
    });

    if (!response.ok) {
      console.error('Failed to fetch ideas for sitemap');
      return [];
    }

    const ideas = await response.json();
    return ideas.map(
      (idea: { id: number; updated_at?: string; created_at: string; score: number }) => ({
        id: idea.id,
        updated_at: idea.updated_at || idea.created_at,
        score: idea.score,
      })
    );
  } catch (error) {
    console.error('Error fetching ideas for sitemap:', error);
    return [];
  }
}

// Fetch popular tags for sitemap
async function getPopularTags(): Promise<SitemapTag[]> {
  try {
    const response = await fetch(`${API_URL}/tags/popular?limit=100`, {
      next: { revalidate: 3600 },
    });

    if (!response.ok) {
      console.error('Failed to fetch tags for sitemap');
      return [];
    }

    const tags = await response.json();
    return tags.map((tag: { name: string; display_name: string; idea_count: number }) => ({
      name: tag.name || tag.display_name,
      idea_count: tag.idea_count,
    }));
  } catch (error) {
    console.error('Error fetching tags for sitemap:', error);
    return [];
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [ideas, tags] = await Promise.all([getApprovedIdeas(), getPopularTags()]);

  const now = new Date();

  // Static pages with language alternates
  const staticEntries: MetadataRoute.Sitemap = staticPages.map((page) => ({
    url: `${BASE_URL}${page.path}`,
    lastModified: now,
    changeFrequency: page.changeFrequency,
    priority: page.priority,
    alternates: {
      languages: {
        'fr-CA': `${BASE_URL}${page.path}`,
        'en-CA': `${BASE_URL}${page.path}`,
      },
    },
  }));

  // Idea pages - higher score ideas get higher priority
  const maxScore = Math.max(...ideas.map((i) => i.score), 1);
  const ideaEntries: MetadataRoute.Sitemap = ideas.map((idea) => ({
    url: `${BASE_URL}/ideas/${idea.id}`,
    lastModified: new Date(idea.updated_at),
    changeFrequency: 'weekly' as const,
    // Priority based on score (0.5-0.9 range)
    priority: 0.5 + (idea.score / maxScore) * 0.4,
    alternates: {
      languages: {
        'fr-CA': `${BASE_URL}/ideas/${idea.id}`,
        'en-CA': `${BASE_URL}/ideas/${idea.id}`,
      },
    },
  }));

  // Tag pages - more ideas = higher priority
  const maxTagCount = Math.max(...tags.map((t) => t.idea_count), 1);
  const tagEntries: MetadataRoute.Sitemap = tags
    .filter((tag) => tag.idea_count > 0)
    .map((tag) => ({
      url: `${BASE_URL}/tags/${encodeURIComponent(tag.name)}`,
      lastModified: now,
      changeFrequency: 'weekly' as const,
      priority: 0.4 + (tag.idea_count / maxTagCount) * 0.3,
      alternates: {
        languages: {
          'fr-CA': `${BASE_URL}/tags/${encodeURIComponent(tag.name)}`,
          'en-CA': `${BASE_URL}/tags/${encodeURIComponent(tag.name)}`,
        },
      },
    }));

  return [...staticEntries, ...ideaEntries, ...tagEntries];
}
