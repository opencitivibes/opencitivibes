import { User } from '@/types';

export interface NavbarContextType {
  user: User | null;
  pathname: string;
  isActive: (href: string) => boolean;
  getNavLinkClass: (href: string) => string;
  getMobileNavLinkClass: (href: string) => string;
  toggleLanguage: () => void;
  logout: () => void;
  closeMobileMenu: () => void;
  closeAdminMenu: () => void;
}

export interface AdminMenuItemsProps {
  variant: 'desktop' | 'mobile';
  onItemClick?: () => void;
}

export interface UserAvatarProps {
  user: User;
  size?: 'sm' | 'md';
  showName?: boolean;
  className?: string;
}
