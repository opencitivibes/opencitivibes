import { serializeSchema, type JsonLdSchema } from '@/lib/seo/structured-data';

interface StructuredDataProps {
  data: JsonLdSchema | JsonLdSchema[];
}

export function StructuredData({ data }: StructuredDataProps) {
  return (
    // nosemgrep: react-dangerouslysetinnerhtml - JSON-LD structured data via JSON.stringify, not user content
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: serializeSchema(data),
      }}
    />
  );
}
