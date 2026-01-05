'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useConfigTranslation } from '@/hooks/useConfigTranslation';
import { useAuthStore } from '@/store/authStore';
import { ideaAPI, categoryAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { Input } from '@/components/Input';
import { RichTextEditor } from '@/components/RichTextEditor';
import { Select } from '@/components/Select';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Card } from '@/components/Card';
import TagInput from '@/components/TagInput';
import SimilarIdeasDialog from '@/components/SimilarIdeasDialog';
import { isContentEmpty, htmlToPlainText } from '@/lib/sanitize';
import type { Category, SimilarIdea } from '@/types';

export default function SubmitIdeaPage() {
  const { t, tc, i18n } = useConfigTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success } = useToast();
  const { getCategoryName } = useLocalizedField();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [tags, setTags] = useState<string[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [similarIdeas, setSimilarIdeas] = useState<SimilarIdea[]>([]);
  const [showSimilarDialog, setShowSimilarDialog] = useState(false);
  const [isCheckingSimilar, setIsCheckingSimilar] = useState(false);
  const [hasCheckedSimilar, setHasCheckedSimilar] = useState(false);

  useEffect(() => {
    if (!user) {
      router.push('/signin?redirect=/submit');
      return;
    }

    loadCategories();
  }, [user, router]);

  // Reset similar check when form content changes significantly
  useEffect(() => {
    setHasCheckedSimilar(false);
    setSimilarIdeas([]);
  }, [title, description, categoryId]);

  const loadCategories = async () => {
    try {
      const data = await categoryAPI.getAll();
      setCategories(data);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!categoryId) {
      setError(t('ideas.categoryRequired'));
      return;
    }

    // Validate description is not empty (handles rich text)
    if (isContentEmpty(description)) {
      setError(t('ideas.descriptionRequired'));
      return;
    }

    // If we haven't checked for similar ideas yet, do that first
    if (!hasCheckedSimilar) {
      setIsCheckingSimilar(true);
      try {
        // Send plain text for similarity comparison
        const similar = await ideaAPI.checkSimilar(
          {
            title,
            description: htmlToPlainText(description),
            category_id: Number(categoryId),
          },
          i18n.language,
          0.3, // threshold
          5 // limit
        );

        if (similar.length > 0) {
          setSimilarIdeas(similar);
          setShowSimilarDialog(true);
          setHasCheckedSimilar(true);
          setIsCheckingSimilar(false);
          return; // Don't proceed with submission yet
        }

        // No similar ideas found, proceed with submission
        setHasCheckedSimilar(true);
      } catch (err) {
        console.error('Error checking similar ideas:', err);
        // If check fails, allow submission anyway
        setHasCheckedSimilar(true);
      } finally {
        setIsCheckingSimilar(false);
      }
    }

    // Proceed with actual submission
    await submitIdea();
  };

  const submitIdea = async () => {
    setIsLoading(true);

    try {
      await ideaAPI.create({
        title,
        description,
        category_id: Number(categoryId),
        tags,
      });

      success('toast.ideaSubmitted');
      router.push('/my-ideas');
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      setError(axiosError.response?.data?.detail || t('common.error'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleProceedAnyway = () => {
    setShowSimilarDialog(false);
    submitIdea();
  };

  const handleCloseSimilarDialog = () => {
    setShowSimilarDialog(false);
    // Reset check flag so user can check again after editing
    setHasCheckedSimilar(false);
  };

  if (!user) {
    return null;
  }

  return (
    <PageContainer maxWidth="4xl" paddingY="normal">
      <PageHeader title={t('ideas.submitIdea')} description={tc('ideas.submitDescription')} />

      <Card>
        {error && (
          <div className="mb-6">
            <Alert variant="error" dismissible onDismiss={() => setError('')}>
              {error}
            </Alert>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <Input
            type="text"
            label={`${t('ideas.title')} *`}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            maxLength={200}
            placeholder={t('ideas.titlePlaceholder', 'Enter a clear and concise title')}
            helperText={`${title.length}/200 ${t('common.characters', 'characters')}`}
          />

          <Select
            label={`${t('ideas.category')} *`}
            value={categoryId}
            onChange={(e) => setCategoryId(Number(e.target.value))}
            required
          >
            <option value="">{t('ideas.selectCategory', 'Select a category')}</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {getCategoryName(category)}
              </option>
            ))}
          </Select>

          <RichTextEditor
            label={`${t('ideas.description')} *`}
            value={description}
            onChange={setDescription}
            placeholder="editor.placeholder"
            helperText={tc('ideas.descriptionHelp')}
            minHeight={200}
            maxLength={10000}
            showCharacterCount
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {t('ideas.tags')} ({t('common.optional')})
            </label>
            <TagInput
              selectedTags={tags}
              onTagsChange={setTags}
              maxTags={5}
              placeholder={t('ideas.addTags')}
            />
          </div>

          <div className="flex flex-col sm:flex-row gap-3 pt-2">
            <Button
              type="submit"
              variant="primary"
              loading={isLoading || isCheckingSimilar}
              disabled={isLoading || isCheckingSimilar}
              className="flex-1 sm:order-2"
            >
              {isCheckingSimilar ? t('ideas.similarIdeas.checking') : t('ideas.submit')}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.back()}
              className="sm:order-1"
            >
              {t('common.cancel')}
            </Button>
          </div>
        </form>
      </Card>

      <SimilarIdeasDialog
        isOpen={showSimilarDialog}
        onClose={handleCloseSimilarDialog}
        onProceed={handleProceedAnyway}
        similarIdeas={similarIdeas}
        isLoading={isLoading}
      />
    </PageContainer>
  );
}
