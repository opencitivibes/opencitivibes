'use client';

import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { ThumbsUp, ThumbsDown, Check } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { voteAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { QualityPopover } from './QualityPopover';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { VoteType, QualityType } from '@/types';

interface VotingButtonsProps {
  ideaId: number;
  upvotes: number;
  downvotes: number;
  score: number;
  userVote: VoteType | null | undefined;
  onVoteUpdate?: () => void;
  variant?: 'compact' | 'full';
  showScore?: boolean;
  /** Content to render after vote buttons (e.g., trust badge) */
  children?: React.ReactNode;
}

export function VotingButtons({
  ideaId,
  upvotes,
  downvotes,
  score,
  userVote,
  onVoteUpdate,
  variant = 'compact',
  showScore = true,
  children,
}: VotingButtonsProps) {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const { success, info, error } = useToast();
  const [isVoting, setIsVoting] = useState(false);
  const [voteAnimating, setVoteAnimating] = useState<'up' | 'down' | null>(null);
  const [showQualityPopover, setShowQualityPopover] = useState(false);
  const [userQualities, setUserQualities] = useState<QualityType[]>([]);
  const upvoteRef = useRef<HTMLButtonElement>(null);

  const handleVote = async (voteType: VoteType, e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (!user || isVoting) return;

    setIsVoting(true);
    setVoteAnimating(voteType === 'upvote' ? 'up' : 'down');

    try {
      if (userVote === voteType) {
        await voteAPI.removeVote(ideaId);
        setShowQualityPopover(false);
        info('toast.voteRemoved');
      } else {
        await voteAPI.vote(ideaId, { vote_type: voteType });
        success('toast.voted');

        // Show quality popover for upvotes
        if (voteType === 'upvote') {
          try {
            const qualities = await voteAPI.getQualities(ideaId);
            setUserQualities(qualities);
          } catch {
            setUserQualities([]);
          }
          setShowQualityPopover(true);
        } else {
          setShowQualityPopover(false);
        }
      }
      onVoteUpdate?.();
    } catch (err) {
      console.error('Vote error:', err);
      const axiosError = err as { response?: { data?: { detail?: string } } };
      const detail = axiosError?.response?.data?.detail;
      if (detail?.includes('own idea')) {
        error('vote.cannotVoteOwnIdea');
      } else {
        error('errors.generic');
      }
    } finally {
      setIsVoting(false);
      setTimeout(() => setVoteAnimating(null), 300);
    }
  };

  const baseButtonClass = `group flex items-center gap-1.5 px-3 py-2 rounded-lg border
    transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary-500
    focus:ring-offset-2 dark:ring-offset-gray-800`;

  const upvoteClass =
    userVote === 'upvote'
      ? 'bg-success-500 dark:bg-success-600 text-white border-success-600 dark:border-success-500 shadow-md shadow-success-200 dark:shadow-success-900/50'
      : 'bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:bg-success-50 dark:hover:bg-success-900/20 hover:border-success-300';

  const downvoteClass =
    userVote === 'downvote'
      ? 'bg-error-500 dark:bg-error-600 text-white border-error-600 dark:border-error-500 shadow-md shadow-error-200 dark:shadow-error-900/50'
      : 'bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-gray-200 dark:border-gray-600 hover:bg-error-50 dark:hover:bg-error-900/20 hover:border-error-300';

  return (
    <div className="flex items-center gap-3">
      {showScore && variant === 'full' && (
        <div className="text-center mr-2">
          <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">{score}</div>
          <div className="text-xs text-gray-500 dark:text-gray-400">{t('ideas.score')}</div>
        </div>
      )}

      <div className="relative">
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              ref={upvoteRef}
              onClick={(e) => handleVote('upvote', e)}
              disabled={isVoting || !user}
              aria-label={t('vote.upvote')}
              aria-pressed={userVote === 'upvote'}
              className={`${baseButtonClass} ${upvoteClass} relative
                ${isVoting || !user ? 'opacity-50 cursor-not-allowed' : ''}
                ${voteAnimating === 'up' ? 'animate-bounce-once' : ''}`}
              style={
                userVote === 'upvote'
                  ? { backgroundColor: '#22c55e', color: 'white', borderColor: '#16a34a' }
                  : undefined
              }
            >
              {userVote === 'upvote' && (
                <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-white rounded-full flex items-center justify-center ring-2 ring-success-500">
                  <Check className="w-2.5 h-2.5 text-success-600" strokeWidth={3} />
                </span>
              )}
              <ThumbsUp
                className={`w-5 h-5 transition-transform duration-200 group-hover:scale-110
                  ${userVote === 'upvote' ? 'fill-white' : ''}`}
                aria-hidden="true"
              />
              <span
                className={`text-sm font-medium tabular-nums ${voteAnimating === 'up' ? 'animate-vote-pulse' : ''}`}
              >
                {upvotes}
              </span>
            </button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{user ? t('vote.upvote') : t('vote.signInToVote')}</p>
          </TooltipContent>
        </Tooltip>
        <QualityPopover
          ideaId={ideaId}
          isOpen={showQualityPopover}
          onClose={() => setShowQualityPopover(false)}
          initialQualities={userQualities}
          anchorRef={upvoteRef}
        />
      </div>

      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={(e) => handleVote('downvote', e)}
            disabled={isVoting || !user}
            aria-label={t('vote.downvote')}
            aria-pressed={userVote === 'downvote'}
            className={`${baseButtonClass} ${downvoteClass} relative
              ${isVoting || !user ? 'opacity-50 cursor-not-allowed' : ''}
              ${voteAnimating === 'down' ? 'animate-bounce-once' : ''}`}
            style={
              userVote === 'downvote'
                ? { backgroundColor: '#ef4444', color: 'white', borderColor: '#dc2626' }
                : undefined
            }
          >
            {userVote === 'downvote' && (
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-white rounded-full flex items-center justify-center ring-2 ring-error-500">
                <Check className="w-2.5 h-2.5 text-error-600" strokeWidth={3} />
              </span>
            )}
            <ThumbsDown
              className={`w-5 h-5 transition-transform duration-200 group-hover:scale-110
                ${userVote === 'downvote' ? 'fill-white' : ''}`}
              aria-hidden="true"
            />
            <span
              className={`text-sm font-medium tabular-nums ${voteAnimating === 'down' ? 'animate-vote-pulse' : ''}`}
            >
              {downvotes}
            </span>
          </button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{user ? t('vote.downvote') : t('vote.signInToVote')}</p>
        </TooltipContent>
      </Tooltip>

      {/* Optional slot for badges/indicators */}
      {children}

      {!user && (
        <span className="text-sm text-gray-500 dark:text-gray-400 italic ml-2">
          {t('vote.signInToVote')}
        </span>
      )}
    </div>
  );
}
