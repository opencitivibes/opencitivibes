import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Soumettre une idée',
  robots: {
    index: false,
    follow: false,
  },
};

export default function SubmitLayout({ children }: { children: React.ReactNode }) {
  return children;
}
