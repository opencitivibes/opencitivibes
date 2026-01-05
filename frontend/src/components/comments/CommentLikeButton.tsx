'use client';

import { useState } from 'react';
import { Heart } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { commentAPI } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

interface CommentLikeButtonProps {
  commentId: number;
  initialLikeCount: number;
  initialUserHasLiked: boolean | null;
  isOwnComment: boolean;
  onLikeChange?: (liked: boolean, count: number) => void;
}

export function CommentLikeButton({
  commentId,
  initialLikeCount,
  initialUserHasLiked,
  isOwnComment,
  onLikeChange,
}: CommentLikeButtonProps) {
  const { t } = useTranslation();
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = user !== null;
  const [likeCount, setLikeCount] = useState(initialLikeCount);
  const [userHasLiked, setUserHasLiked] = useState(initialUserHasLiked ?? false);
  const [isLoading, setIsLoading] = useState(false);

  const canLike = isAuthenticated && !isOwnComment;

  const handleClick = async () => {
    if (!canLike || isLoading) return;

    // Optimistic update
    const newLiked = !userHasLiked;
    const newCount = newLiked ? likeCount + 1 : likeCount - 1;
    setUserHasLiked(newLiked);
    setLikeCount(newCount);

    setIsLoading(true);
    try {
      const response = await commentAPI.toggleLike(commentId);
      // Sync with server response
      setUserHasLiked(response.liked);
      setLikeCount(response.like_count);
      onLikeChange?.(response.liked, response.like_count);
    } catch {
      // Revert optimistic update
      setUserHasLiked(!newLiked);
      setLikeCount(likeCount);
    } finally {
      setIsLoading(false);
    }
  };

  const getTooltip = (): string => {
    if (!isAuthenticated) return t('comments.loginToLike');
    if (isOwnComment) return t('comments.cannotLikeOwn');
    return userHasLiked ? t('comments.unlike') : t('comments.like');
  };

  const baseClasses = 'flex items-center gap-1 text-sm transition-colors rounded px-1.5 py-0.5';
  const interactiveClasses = canLike
    ? 'hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 cursor-pointer'
    : 'cursor-not-allowed opacity-50';
  const likedClasses = userHasLiked ? 'text-red-500' : 'text-gray-500 dark:text-gray-400';

  return (
    <button
      onClick={handleClick}
      disabled={!canLike || isLoading}
      title={getTooltip()}
      className={`${baseClasses} ${interactiveClasses} ${likedClasses}`}
      aria-label={getTooltip()}
      aria-pressed={userHasLiked}
    >
      <Heart
        className={`h-4 w-4 transition-all ${userHasLiked ? 'fill-current' : ''} ${isLoading ? 'animate-pulse' : ''}`}
      />
      <span className="min-w-[1rem] text-center">{likeCount}</span>
    </button>
  );
}
