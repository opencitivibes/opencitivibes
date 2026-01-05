'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
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
import { isContentEmpty } from '@/lib/sanitize';
import type { Category, Idea } from '@/types';

export default function EditIdeaPage() {
  const { t, tc } = useConfigTranslation();
  const router = useRouter();
  const params = useParams();
  const ideaId = Number(params.id);
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();
  const { getCategoryName } = useLocalizedField();

  const [idea, setIdea] = useState<Idea | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [categoryId, setCategoryId] = useState<number | ''>('');
  const [tags, setTags] = useState<string[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingIdea, setIsLoadingIdea] = useState(true);

  useEffect(() => {
    if (!user) {
      router.push(`/signin?redirect=/ideas/${ideaId}/edit`);
      return;
    }

    loadCategories();
    loadIdea();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, router, ideaId]);

  const loadCategories = async () => {
    try {
      const data = await categoryAPI.getAll();
      setCategories(data);
    } catch (err) {
      console.error('Error loading categories:', err);
    }
  };

  const loadIdea = async () => {
    try {
      setIsLoadingIdea(true);
      const data = await ideaAPI.getOne(ideaId);
      setIdea(data);

      // Check ownership
      if (data.user_id !== user?.id) {
        toastError(t('ideas.notOwner', 'You can only edit your own ideas'), { isRaw: true });
        router.push(`/ideas/${ideaId}`);
        return;
      }

      // Check if idea is editable (only pending or rejected)
      if (data.status === 'approved') {
        toastError(t('ideas.cannotEditApproved', 'Approved ideas cannot be edited'), {
          isRaw: true,
        });
        router.push(`/ideas/${ideaId}`);
        return;
      }

      // Populate form with existing data
      setTitle(data.title);
      setDescription(data.description);
      setCategoryId(data.category_id);
      setTags(data.tags?.map((tag) => tag.display_name) || []);
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error loading idea:', err);
      setError(axiosError.response?.data?.detail || t('common.error'));
    } finally {
      setIsLoadingIdea(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!categoryId) {
      setError(t('ideas.categoryRequired'));
      return;
    }

    if (isContentEmpty(description)) {
      setError(t('ideas.descriptionRequired'));
      return;
    }

    setIsLoading(true);

    try {
      await ideaAPI.update(ideaId, {
        title,
        description,
        category_id: Number(categoryId),
        tags,
      });

      success('toast.ideaUpdated');
      router.push(`/ideas/${ideaId}`);
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      setError(axiosError.response?.data?.detail || t('common.error'));
    } finally {
      setIsLoading(false);
    }
  };

  if (!user) {
    return null;
  }

  if (isLoadingIdea) {
    return (
      <PageContainer maxWidth="4xl" paddingY="normal">
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-primary-500"></div>
          <p className="mt-4 text-gray-500">{t('common.loading')}</p>
        </div>
      </PageContainer>
    );
  }

  if (!idea) {
    return (
      <PageContainer maxWidth="4xl" paddingY="normal">
        <Alert variant="error" title={t('common.error')}>
          {error || t('ideas.notFound', 'Idea not found')}
        </Alert>
        <div className="mt-4">
          <Button variant="ghost" onClick={() => router.push('/')}>
            {t('common.backToHome', 'Back to Home')}
          </Button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer maxWidth="4xl" paddingY="normal">
      <PageHeader
        title={t('ideas.editIdea', 'Edit Idea')}
        description={t('ideas.editDescription', 'Update your idea and resubmit for approval')}
      />

      {/* Info alert for rejected ideas */}
      {idea.status === 'rejected' && (
        <div className="mb-6">
          <Alert variant="info">
            {t(
              'ideas.editRejectedInfo',
              'Editing this idea will resubmit it for approval. Make changes based on the admin feedback below.'
            )}
          </Alert>
          {idea.admin_comment && (
            <Alert variant="warning" className="mt-3">
              <strong>{t('ideas.adminComment')}:</strong> {idea.admin_comment}
            </Alert>
          )}
        </div>
      )}

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
            <label className="block text-sm font-medium text-gray-700 mb-2">
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
              loading={isLoading}
              disabled={isLoading}
              className="flex-1 sm:order-2"
            >
              {t('ideas.saveChanges', 'Save Changes')}
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push(`/ideas/${ideaId}`)}
              className="sm:order-1"
            >
              {t('common.cancel')}
            </Button>
          </div>
        </form>
      </Card>
    </PageContainer>
  );
}
