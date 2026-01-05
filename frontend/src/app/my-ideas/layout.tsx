import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Mes idées',
  robots: {
    index: false,
    follow: false,
  },
};

export default function MyIdeasLayout({ children }: { children: React.ReactNode }) {
  return children;
}
