import Link from 'next/link';

interface TagBadgeProps {
  tag: string;
  clickable?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

export default function TagBadge({
  tag,
  clickable = true,
  size = 'sm',
  className = '',
}: TagBadgeProps) {
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm',
  };

  const baseClasses = `inline-flex items-center ${sizeClasses[size]} bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300 rounded-full hover:bg-primary-200 dark:hover:bg-primary-800 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-1 dark:focus:ring-offset-gray-800 ${className}`;

  if (clickable) {
    return (
      <Link
        href={`/tags/${encodeURIComponent(tag.toLowerCase())}`}
        className={baseClasses}
        onClick={(e) => e.stopPropagation()}
        aria-label={`Filter by tag: ${tag}`}
      >
        {tag}
      </Link>
    );
  }

  return <span className={baseClasses}>{tag}</span>;
}
