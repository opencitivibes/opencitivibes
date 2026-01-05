'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { ideaAPI, commentAPI, adminAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { Badge } from '@/components/Badge';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import { LanguageBadge } from '@/components/LanguageBadge';
import { PageContainer } from '@/components/PageContainer';
import { Card } from '@/components/Card';
import { RichTextDisplay } from '@/components/RichTextDisplay';
import { DeleteIdeaDialog } from '@/components/DeleteIdeaDialog';
import { DeleteCommentDialog } from '@/components/DeleteCommentDialog';
import { VotingButtons } from '@/components/VotingButtons';
import { QualityBreakdown } from '@/components/QualityBreakdown';
import { FlagButton } from '@/components/moderation';
import { CommentLikeButton, CommentSortSelector } from '@/components/comments';
import type { CommentSortOrder } from '@/components/comments';
import { isContentEmpty } from '@/lib/sanitize';
import { htmlToPlainText } from '@/lib/sanitize';
import type { Idea, Comment } from '@/types';

// Lazy load the simple editor since it's below the fold
const SimpleRichTextEditor = dynamic(
  () => import('@/components/RichTextEditor').then((mod) => mod.SimpleRichTextEditor),
  {
    loading: () => (
      <div className="border border-gray-300 dark:border-gray-600 rounded-lg animate-pulse">
        <div className="h-8 bg-gray-100 dark:bg-gray-700 rounded-t-lg" />
        <div className="h-20 bg-gray-50 dark:bg-gray-800 rounded-b-lg" />
      </div>
    ),
    ssr: false,
  }
);

interface IdeaDetailClientProps {
  ideaId: string;
}

export default function IdeaDetailClient({ ideaId }: IdeaDetailClientProps) {
  const { t } = useTranslation();
  const router = useRouter();
  const { user } = useAuthStore();
  const { getField, formatDate, getDisplayName } = useLocalizedField();
  const { success, error: toastError } = useToast();
  const numericIdeaId = Number(ideaId);

  const [idea, setIdea] = useState<Idea | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [commentText, setCommentText] = useState('');
  const [submittingComment, setSubmittingComment] = useState(false);
  const [commentSortOrder, setCommentSortOrder] = useState<CommentSortOrder>('relevance');

  useEffect(() => {
    loadIdea();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numericIdeaId]);

  const loadIdea = async (showLoadingSpinner = true) => {
    try {
      if (showLoadingSpinner) {
        setLoading(true);
      }
      const data = await ideaAPI.getOne(numericIdeaId);
      setIdea(data);
      setError(null);
      // Only load comments for approved ideas
      if (data.status === 'approved') {
        loadComments();
      }
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error loading idea:', err);
      setError(axiosError.response?.data?.detail || t('common.error'));
    } finally {
      if (showLoadingSpinner) {
        setLoading(false);
      }
    }
  };

  // Refresh idea data without showing loading spinner (preserves child component state)
  const refreshIdea = () => loadIdea(false);

  const loadComments = async (sortBy: CommentSortOrder = commentSortOrder) => {
    try {
      const data = await commentAPI.getForIdea(numericIdeaId, 0, 50, sortBy);
      setComments(data);
    } catch (err) {
      console.error('Error loading comments:', err);
    }
  };

  // Reload comments when sort order changes
  useEffect(() => {
    if (idea?.status === 'approved') {
      loadComments(commentSortOrder);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [commentSortOrder]);

  const handleSubmitComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || isContentEmpty(commentText)) return;

    setSubmittingComment(true);
    try {
      await commentAPI.create(numericIdeaId, { content: commentText });
      success('toast.commentPosted');
      setCommentText('');
      await loadComments();
      await loadIdea();
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error submitting comment:', err);
      toastError(axiosError.response?.data?.detail || t('common.error'), { isRaw: true });
    } finally {
      setSubmittingComment(false);
    }
  };

  const handleDeleteComment = async (commentId: number) => {
    try {
      await commentAPI.delete(commentId);
      success('toast.commentDeleted');
      await loadComments();
      await loadIdea();
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error deleting comment:', err);
      toastError(axiosError.response?.data?.detail || t('common.error'), { isRaw: true });
      throw err; // Re-throw for DeleteCommentDialog
    }
  };

  // Delete functionality
  const isOwner = user && idea && user.id === idea.user_id;
  const isAdmin = user?.is_global_admin;

  const handleDeleteIdea = async (reason?: string) => {
    if (!idea) return;

    if (isAdmin && !isOwner) {
      // Admin deleting someone else's idea - reason is required
      await adminAPI.ideas.delete(idea.id, reason!);
    } else {
      // User deleting own idea
      await ideaAPI.delete(idea.id, reason);
    }
  };

  const handleDeleteSuccess = () => {
    if (isAdmin && !isOwner) {
      success('toast.ideaDeletedByAdmin');
    } else {
      success('toast.ideaDeletedByUser');
    }
    router.push('/');
  };

  if (loading) {
    return (
      <PageContainer maxWidth="4xl" paddingY="normal">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 dark:border-gray-700 border-t-primary-500"></div>
          <p className="mt-4 text-gray-500 dark:text-gray-400">{t('common.loading')}</p>
        </div>
      </PageContainer>
    );
  }

  if (error || !idea) {
    return (
      <PageContainer maxWidth="4xl" paddingY="normal">
        <Alert variant="error" title={t('common.error')}>
          {error || t('ideas.notFound', 'Idea not found')}
        </Alert>
        <div className="mt-4">
          <Button variant="ghost" onClick={() => router.push('/')}>
            ← {t('common.backToHome', 'Back to Home')}
          </Button>
        </div>
      </PageContainer>
    );
  }

  const categoryName = getField(
    { name_fr: idea.category_name_fr, name_en: idea.category_name_en },
    'name'
  );

  return (
    <PageContainer maxWidth="4xl" paddingY="normal">
      {/* Back Button */}
      <Button variant="ghost" onClick={() => router.push('/')} className="mb-6">
        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        {t('common.back', 'Back')}
      </Button>

      {/* Idea Details */}
      <Card className="mb-6 overflow-visible">
        {/* Header */}
        <div className="mb-4">
          <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
            <div className="flex flex-wrap gap-2">
              <Badge variant="primary">{categoryName}</Badge>
              <Badge variant={idea.status as 'pending' | 'approved' | 'rejected'}>
                {t(`ideas.status.${idea.status}`)}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              {/* Flag button for other users' ideas */}
              <FlagButton
                contentType="idea"
                contentId={idea.id}
                contentAuthorId={idea.user_id}
                contentPreview={`${idea.title}: ${htmlToPlainText(idea.description).slice(0, 200)}`}
                variant="text"
              />
              {/* Edit button for owner of pending/rejected ideas */}
              {isOwner && idea.status !== 'approved' && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => router.push(`/ideas/${idea.id}/edit`)}
                >
                  {t('common.edit', 'Edit')}
                </Button>
              )}
              {/* Delete button for owner or admin */}
              {(isOwner || isAdmin) && (
                <DeleteIdeaDialog
                  ideaTitle={idea.title}
                  isAdmin={isAdmin && !isOwner}
                  onDelete={handleDeleteIdea}
                  onSuccess={handleDeleteSuccess}
                />
              )}
            </div>
          </div>
          <div className="flex items-center gap-3 flex-wrap mb-2">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">{idea.title}</h1>
            <LanguageBadge language={idea.language} size="md" />
          </div>
          <div className="flex items-center text-sm text-gray-500 dark:text-gray-400">
            <span>
              {t('ideas.postedBy')}:{' '}
              <span className="font-medium">{getDisplayName(idea.author_display_name)}</span>
            </span>
            <span className="mx-2">•</span>
            <span>
              {formatDate(idea.created_at, {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })}
            </span>
          </div>
        </div>

        {/* Description */}
        <div className="mb-6">
          <RichTextDisplay
            content={idea.description}
            className="text-gray-700 dark:text-gray-300"
          />
        </div>

        {/* Voting Section */}
        {idea.status === 'approved' && (
          <div className="border-t border-gray-200 dark:border-gray-700 pt-6 overflow-visible">
            <VotingButtons
              ideaId={idea.id}
              upvotes={idea.upvotes}
              downvotes={idea.downvotes}
              score={idea.score}
              userVote={idea.user_vote}
              onVoteUpdate={refreshIdea}
              variant="full"
              showScore={true}
            />
            {/* Quality Breakdown */}
            {idea.quality_counts && (
              <QualityBreakdown counts={idea.quality_counts} totalUpvotes={idea.upvotes} />
            )}
          </div>
        )}

        {/* Admin Comment (if rejected) */}
        {idea.status === 'rejected' && idea.admin_comment && (
          <div className="mt-6">
            <Alert variant="error" title={t('ideas.adminComment')}>
              {idea.admin_comment}
            </Alert>
          </div>
        )}
      </Card>

      {/* Comments Section - only for approved ideas */}
      {idea.status === 'approved' && (
        <Card>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              {t('comments.title', 'Comments')} ({comments.length})
            </h2>
            {comments.length > 1 && (
              <CommentSortSelector value={commentSortOrder} onChange={setCommentSortOrder} />
            )}
          </div>

          {/* Comment Form */}
          {user ? (
            <form onSubmit={handleSubmitComment} className="mb-8">
              <SimpleRichTextEditor
                value={commentText}
                onChange={setCommentText}
                placeholder="editor.placeholderComment"
                rows={3}
                disabled={submittingComment}
                maxLength={2000}
                showCharacterCount
              />
              <div className="mt-3 flex justify-end">
                <Button
                  type="submit"
                  variant="primary"
                  disabled={submittingComment || isContentEmpty(commentText)}
                  loading={submittingComment}
                >
                  {t('comments.submit', 'Submit Comment')}
                </Button>
              </div>
            </form>
          ) : (
            <div className="mb-8">
              <Alert variant="info">
                {t('comments.signInToComment', 'Please sign in to comment')}
              </Alert>
            </div>
          )}

          {/* Comments List */}
          {comments.length === 0 ? (
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gray-100 dark:bg-gray-700 mb-4">
                <svg
                  className="w-8 h-8 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <p className="text-gray-600 dark:text-gray-300 font-medium">
                {t('comments.noComments', 'No comments yet. Be the first to comment!')}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {comments.map((comment) => (
                <div
                  key={comment.id}
                  className={`p-4 rounded-lg border ${
                    comment.is_moderated
                      ? 'bg-error-50 dark:bg-error-900/20 border-error-200 dark:border-error-800'
                      : 'bg-gray-50 dark:bg-gray-700/50 border-gray-200 dark:border-gray-600'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900 dark:text-gray-100">
                        {getDisplayName(comment.author_display_name)}
                      </span>
                      <LanguageBadge language={comment.language} size="sm" />
                      {comment.is_moderated && (
                        <Badge variant="error" size="sm">
                          {t('comments.moderated', 'Moderated')}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {formatDate(comment.created_at, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                      <div className="flex items-center gap-2">
                        <CommentLikeButton
                          commentId={comment.id}
                          initialLikeCount={comment.like_count}
                          initialUserHasLiked={comment.user_has_liked}
                          isOwnComment={user?.id === comment.user_id}
                        />
                        <FlagButton
                          contentType="comment"
                          contentId={comment.id}
                          contentAuthorId={comment.user_id}
                          contentPreview={htmlToPlainText(comment.content).slice(0, 200)}
                        />
                        {user && user.id === comment.user_id && (
                          <DeleteCommentDialog onDelete={() => handleDeleteComment(comment.id)} />
                        )}
                      </div>
                    </div>
                  </div>
                  <div className={comment.is_moderated ? 'line-through opacity-70' : ''}>
                    <RichTextDisplay
                      content={comment.content}
                      className="text-gray-700 dark:text-gray-300 text-sm"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </PageContainer>
  );
}
