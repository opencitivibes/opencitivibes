import type { Metadata } from 'next';
import { generateIdeaMetadata, siteConfig } from '@/lib/seo/metadata';
import { generateIdeaSchema, generateBreadcrumbSchema } from '@/lib/seo/structured-data';
import { StructuredData } from '@/components/seo/StructuredData';
import { serverIdeaAPI } from '@/lib/api-server';
import IdeaDetailClient from '@/components/pages/IdeaDetailClient';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const idea = await serverIdeaAPI.getOne(id);

  if (!idea) {
    return {
      title: 'Idée non trouvée',
      description: "Cette idée n'existe pas ou a été supprimée.",
    };
  }

  return generateIdeaMetadata(idea, 'fr');
}

// Enable static generation for popular ideas
export async function generateStaticParams() {
  const ideas = await serverIdeaAPI.getLeaderboard(50);
  return ideas.map((idea) => ({
    id: idea.id.toString(),
  }));
}

export default async function IdeaDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const idea = await serverIdeaAPI.getOne(id);

  // If idea not found on server (e.g., pending idea that requires auth),
  // still render the client component which will fetch with auth token.
  // The client component handles its own error/loading states.
  if (!idea) {
    return <IdeaDetailClient ideaId={id} />;
  }

  // Generate structured data for approved ideas
  const ideaSchema = generateIdeaSchema(idea, 'fr');
  const breadcrumbSchema = generateBreadcrumbSchema([
    { name: 'Accueil', url: siteConfig.url },
    { name: idea.category_name_fr || 'Idées', url: siteConfig.url },
    { name: idea.title, url: `${siteConfig.url}/ideas/${idea.id}` },
  ]);

  return (
    <>
      <StructuredData data={[ideaSchema, breadcrumbSchema]} />
      <IdeaDetailClient ideaId={id} />
    </>
  );
}
