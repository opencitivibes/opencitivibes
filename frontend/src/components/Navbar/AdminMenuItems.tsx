'use client';

import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { Shield, Bell, UserCog } from 'lucide-react';
import {
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';

interface AdminMenuItemsProps {
  variant: 'desktop' | 'mobile';
  getMobileNavLinkClass?: (href: string) => string;
  onItemClick?: () => void;
}

// SVG Icons as components for reuse
const PendingIdeasIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
    />
  </svg>
);

const FlaggedIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"
    />
  </svg>
);

const CommentsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
    />
  </svg>
);

const AppealsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"
    />
  </svg>
);

const CategoriesIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
    />
  </svg>
);

const UsersIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
    />
  </svg>
);

const DeletedIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
    />
  </svg>
);

const RejectedIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
    />
  </svg>
);

const AnalyticsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
    />
  </svg>
);

const QualitiesIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
    />
  </svg>
);

const StatsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
    />
  </svg>
);

const DiagnosticsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
    />
  </svg>
);

// Menu items configuration
const menuSections = [
  {
    labelKey: 'nav.sectionModeration',
    items: [
      { href: '/admin', labelKey: 'nav.pendingIdeas', Icon: PendingIdeasIcon },
      { href: '/admin/moderation', labelKey: 'nav.flaggedContent', Icon: FlaggedIcon },
      {
        href: '/admin/moderation/pending-comments',
        labelKey: 'nav.pendingComments',
        Icon: CommentsIcon,
      },
      { href: '/admin/moderation/appeals', labelKey: 'nav.appeals', Icon: AppealsIcon },
    ],
  },
  {
    labelKey: 'nav.sectionManagement',
    items: [
      { href: '/admin/categories', labelKey: 'nav.categories', Icon: CategoriesIcon },
      { href: '/admin/users', labelKey: 'nav.users', Icon: UsersIcon },
      { href: '/admin/deleted-ideas', labelKey: 'nav.deletedIdeas', Icon: DeletedIcon },
      { href: '/admin/rejected-ideas', labelKey: 'nav.rejectedIdeas', Icon: RejectedIcon },
      {
        href: '/admin/officials',
        labelKey: 'nav.officials',
        Icon: () => <Shield className="w-4 h-4" />,
      },
      {
        href: '/admin/category-admins',
        labelKey: 'nav.categoryAdmins',
        Icon: () => <UserCog className="w-4 h-4" />,
      },
    ],
  },
  {
    labelKey: 'nav.sectionInsights',
    items: [
      { href: '/admin/analytics', labelKey: 'nav.analytics', Icon: AnalyticsIcon },
      { href: '/admin/analytics/qualities', labelKey: 'nav.qualityAnalytics', Icon: QualitiesIcon },
      { href: '/admin/moderation/stats', labelKey: 'nav.moderationStats', Icon: StatsIcon },
      {
        href: '/admin/notifications',
        labelKey: 'nav.notifications',
        Icon: () => <Bell className="w-4 h-4" />,
      },
    ],
  },
  {
    labelKey: 'nav.sectionSystem',
    items: [{ href: '/admin/diagnostics', labelKey: 'nav.diagnostics', Icon: DiagnosticsIcon }],
  },
];

export function AdminMenuItemsDesktop({ onItemClick }: { onItemClick?: () => void }) {
  const { t } = useTranslation();

  return (
    <>
      {menuSections.map((section, sectionIndex) => (
        <div key={section.labelKey}>
          {sectionIndex > 0 && <DropdownMenuSeparator />}
          <DropdownMenuLabel className="text-xs text-gray-500 dark:text-gray-400 uppercase">
            {t(section.labelKey)}
          </DropdownMenuLabel>
          {section.items.map((item) => (
            <DropdownMenuItem key={item.href} asChild>
              <Link
                href={item.href}
                className="cursor-pointer flex items-center gap-2"
                onClick={onItemClick}
              >
                <item.Icon />
                {t(item.labelKey)}
              </Link>
            </DropdownMenuItem>
          ))}
        </div>
      ))}
    </>
  );
}

export function AdminMenuItemsMobile({
  getMobileNavLinkClass,
  onItemClick,
}: {
  getMobileNavLinkClass: (href: string) => string;
  onItemClick?: () => void;
}) {
  const { t } = useTranslation();

  return (
    <div className="border-t border-gray-200 dark:border-gray-700 pt-3 mt-3">
      {menuSections.map((section, sectionIndex) => (
        <div key={section.labelKey}>
          <div
            className={`text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide ${sectionIndex > 0 ? 'mt-4' : ''} mb-2 px-3`}
          >
            {t(section.labelKey)}
          </div>
          {section.items.map((item) => {
            const isOfficials = item.href === '/admin/officials';
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`${getMobileNavLinkClass(item.href)} ${isOfficials ? 'flex items-center gap-2' : ''}`}
                onClick={onItemClick}
              >
                {isOfficials && <Shield className="w-4 h-4" />}
                {t(item.labelKey)}
              </Link>
            );
          })}
        </div>
      ))}
    </div>
  );
}

export type { AdminMenuItemsProps };
