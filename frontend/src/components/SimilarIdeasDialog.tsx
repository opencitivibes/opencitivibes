'use client';

import { useTranslation } from 'react-i18next';
import { AlertTriangle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import type { SimilarIdea } from '@/types';

interface SimilarIdeasDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onProceed: () => void;
  similarIdeas: SimilarIdea[];
  isLoading?: boolean;
}

export default function SimilarIdeasDialog({
  isOpen,
  onClose,
  onProceed,
  similarIdeas,
  isLoading = false,
}: SimilarIdeasDialogProps) {
  const { t } = useTranslation();

  const handleViewIdea = (ideaId: number) => {
    // Open in new tab to preserve form state
    window.open(`/ideas/${ideaId}`, '_blank');
  };

  // Format similarity score as percentage
  const formatSimilarity = (score: number): string => {
    return Math.round(score * 100).toString();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-warning-500" aria-hidden="true" />
            {t('ideas.similarIdeas.title')}
          </DialogTitle>
          <DialogDescription>{t('ideas.similarIdeas.description')}</DialogDescription>
        </DialogHeader>

        {/* Warning Alert */}
        <Alert variant="warning" className="my-4">
          {t('ideas.similarIdeas.warningMessage')}
        </Alert>

        {/* Similar Ideas List */}
        <div className="space-y-4">
          <p className="text-sm text-gray-600 font-medium">
            {t('ideas.similarIdeas.foundCount', { count: similarIdeas.length })}
          </p>

          {similarIdeas.map((idea) => (
            <div
              key={idea.id}
              className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition"
            >
              <div className="flex justify-between items-start mb-2">
                <h4 className="font-semibold text-gray-900 flex-1">{idea.title}</h4>
                <div className="flex items-center gap-2 ml-4">
                  <span className="px-2 py-1 bg-primary-100 text-primary-700 text-sm rounded font-medium">
                    {t('ideas.similarIdeas.similarityScore', {
                      score: formatSimilarity(idea.similarity_score),
                    })}
                  </span>
                </div>
              </div>

              <p className="text-gray-600 text-sm mb-3 line-clamp-2">{idea.description}</p>

              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">
                  {t('ideas.similarIdeas.ideaScore', { score: idea.score })}
                </span>
                <Button size="sm" variant="secondary" onClick={() => handleViewIdea(idea.id)}>
                  {t('ideas.similarIdeas.viewIdea')} →
                </Button>
              </div>
            </div>
          ))}
        </div>

        <DialogFooter className="flex flex-col sm:flex-row gap-3 mt-6">
          <Button variant="secondary" onClick={onClose} className="sm:order-1">
            {t('ideas.similarIdeas.cancel')}
          </Button>
          <Button
            variant="primary"
            onClick={onProceed}
            loading={isLoading}
            disabled={isLoading}
            className="sm:order-2"
          >
            {t('ideas.similarIdeas.proceedAnyway')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
