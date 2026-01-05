'use client';

import Image, { ImageProps } from 'next/image';
import { useState } from 'react';

interface OptimizedImageProps extends Omit<ImageProps, 'onLoad' | 'onError'> {
  fallbackSrc?: string;
  aspectRatio?: string;
  wrapperClassName?: string;
}

/**
 * Optimized image component with:
 * - Lazy loading by default
 * - Error fallback
 * - Aspect ratio preservation (prevents CLS)
 * - Skeleton loading state
 */
export function OptimizedImage({
  src,
  alt,
  fallbackSrc = '/images/placeholder.png',
  aspectRatio,
  wrapperClassName = '',
  className = '',
  priority = false,
  ...props
}: OptimizedImageProps) {
  const [error, setError] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const imageSrc = error ? fallbackSrc : src;

  return (
    <div
      className={`relative overflow-hidden ${wrapperClassName}`}
      style={aspectRatio ? { aspectRatio } : undefined}
    >
      <Image
        src={imageSrc}
        alt={alt}
        className={`
          transition-opacity duration-300
          ${loaded ? 'opacity-100' : 'opacity-0'}
          ${className}
        `}
        onError={() => setError(true)}
        onLoad={() => setLoaded(true)}
        priority={priority}
        loading={priority ? 'eager' : 'lazy'}
        {...props}
      />
      {/* Skeleton placeholder while loading */}
      {!loaded && <div className="absolute inset-0 bg-gray-200 animate-pulse" aria-hidden="true" />}
    </div>
  );
}
