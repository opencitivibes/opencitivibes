import type { Metadata } from 'next';
import { generateTagMetadata, siteConfig } from '@/lib/seo/metadata';
import { generateCollectionPageSchema, generateBreadcrumbSchema } from '@/lib/seo/structured-data';
import { StructuredData } from '@/components/seo/StructuredData';
import { serverTagAPI } from '@/lib/api-server';
import TagPageClient from '@/components/pages/TagPageClient';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ tag: string }>;
}): Promise<Metadata> {
  const { tag } = await params;
  const decodedTag = decodeURIComponent(tag);
  const stats = await serverTagAPI.getStatsByName(decodedTag);

  return generateTagMetadata(decodedTag, stats?.approved_ideas || 0, 'fr');
}

export default async function TagPage({ params }: { params: Promise<{ tag: string }> }) {
  const { tag } = await params;
  const decodedTag = decodeURIComponent(tag);
  const stats = await serverTagAPI.getStatsByName(decodedTag);

  const collectionSchema = generateCollectionPageSchema(
    `#${decodedTag}`,
    `Idées étiquetées avec #${decodedTag}`,
    `${siteConfig.url}/tags/${tag}`,
    stats?.approved_ideas || 0,
    'fr'
  );

  const breadcrumbSchema = generateBreadcrumbSchema([
    { name: 'Accueil', url: siteConfig.url },
    { name: 'Étiquettes', url: `${siteConfig.url}/tags` },
    { name: `#${decodedTag}`, url: `${siteConfig.url}/tags/${tag}` },
  ]);

  return (
    <>
      <StructuredData data={[collectionSchema, breadcrumbSchema]} />
      <TagPageClient tagName={tag} />
    </>
  );
}
