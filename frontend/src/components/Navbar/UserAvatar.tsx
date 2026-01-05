import Image from 'next/image';
import { User } from '@/types';
import { getAvatarUrl } from './utils';

interface UserAvatarProps {
  user: User;
  size?: 'sm' | 'md';
  className?: string;
}

const sizeClasses = {
  sm: 'w-8 h-8',
  md: 'w-10 h-10',
};

const sizePx = {
  sm: 32,
  md: 40,
};

export function UserAvatar({ user, size = 'sm', className = '' }: UserAvatarProps) {
  const sizeClass = sizeClasses[size];
  const px = sizePx[size];

  if (user.avatar_url) {
    return (
      <Image
        src={getAvatarUrl(user.avatar_url)}
        alt={user.display_name || user.username}
        width={px}
        height={px}
        className={`${sizeClass} rounded-full object-cover ${className}`}
        unoptimized
      />
    );
  }

  return (
    <div
      className={`${sizeClass} rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center text-white font-semibold ${size === 'sm' ? 'text-sm' : ''} ${className}`}
    >
      {user.display_name?.charAt(0).toUpperCase() || user.username?.charAt(0).toUpperCase()}
    </div>
  );
}
