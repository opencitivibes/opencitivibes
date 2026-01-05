'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { adminAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { Button } from '@/components/Button';
import { Input } from '@/components/Input';
import { Textarea } from '@/components/Textarea';
import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { CategoryStatistics, CategoryCreate } from '@/types';

type ModalMode = 'create' | 'edit' | 'delete' | null;

interface CategoryFormData extends CategoryCreate {
  id?: number;
}

export default function AdminCategoriesPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();
  const { getCategoryName } = useLocalizedField();

  const [categories, setCategories] = useState<CategoryStatistics[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedCategory, setSelectedCategory] = useState<CategoryStatistics | null>(null);
  const [formData, setFormData] = useState<CategoryFormData>({
    name_en: '',
    name_fr: '',
    description_en: '',
    description_fr: '',
  });
  const [error, setError] = useState<string>('');

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
      return;
    }

    loadCategories();
  }, [user, router]);

  const loadCategories = async () => {
    try {
      const data = await adminAPI.getAllCategories();
      setCategories(data);
    } catch (error) {
      console.error('Error loading categories:', error);
      setError('Failed to load categories');
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name_en: '',
      name_fr: '',
      description_en: '',
      description_fr: '',
    });
    setSelectedCategory(null);
    setModalMode(null);
    setError('');
  };

  const handleOpenCreate = () => {
    resetForm();
    setModalMode('create');
  };

  const handleOpenEdit = (category: CategoryStatistics) => {
    setSelectedCategory(category);
    setFormData({
      id: category.category_id,
      name_en: category.category_name_en,
      name_fr: category.category_name_fr,
      description_en: '',
      description_fr: '',
    });
    setModalMode('edit');
  };

  const handleOpenDelete = (category: CategoryStatistics) => {
    setSelectedCategory(category);
    setModalMode('delete');
  };

  const handleCreate = async () => {
    if (!formData.name_en.trim() || !formData.name_fr.trim()) {
      setError('Both English and French names are required');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await adminAPI.createCategory({
        name_en: formData.name_en.trim(),
        name_fr: formData.name_fr.trim(),
        description_en: formData.description_en?.trim() || undefined,
        description_fr: formData.description_fr?.trim() || undefined,
      });
      success('toast.categoryCreated');
      await loadCategories();
      resetForm();
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error creating category:', err);
      toastError(axiosError.response?.data?.detail || t('toast.error'), { isRaw: true });
      setError(axiosError.response?.data?.detail || 'Failed to create category');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdate = async () => {
    if (!selectedCategory || !formData.name_en.trim() || !formData.name_fr.trim()) {
      setError('Both English and French names are required');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await adminAPI.updateCategory(selectedCategory.category_id, {
        name_en: formData.name_en.trim(),
        name_fr: formData.name_fr.trim(),
        description_en: formData.description_en?.trim() || undefined,
        description_fr: formData.description_fr?.trim() || undefined,
      });
      success('toast.categoryUpdated');
      await loadCategories();
      resetForm();
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error updating category:', err);
      toastError(axiosError.response?.data?.detail || t('toast.error'), { isRaw: true });
      setError(axiosError.response?.data?.detail || 'Failed to update category');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedCategory) return;

    setIsSubmitting(true);
    setError('');

    try {
      await adminAPI.deleteCategory(selectedCategory.category_id);
      success('toast.categoryDeleted');
      await loadCategories();
      resetForm();
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error deleting category:', err);
      toastError(axiosError.response?.data?.detail || t('toast.error'), { isRaw: true });
      setError(
        axiosError.response?.data?.detail || 'Failed to delete category. It may contain ideas.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <PageHeader
        title={t('admin.categories.title')}
        actions={
          <Button variant="primary" onClick={handleOpenCreate}>
            {t('admin.categories.createButton')}
          </Button>
        }
      />

      {/* Categories List */}
      <Card>
        <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
          {t('admin.categories.allCategories')} ({categories.length})
        </h2>

        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-primary-500"></div>
            <p className="mt-4 text-gray-500">{t('common.loading')}</p>
          </div>
        ) : categories.length === 0 ? (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary-50 mb-6">
              <svg
                className="w-10 h-10 text-primary-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              {t('admin.categories.noCategoriesFound')}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {t('admin.categories.createFirst')}
            </p>
            <Button variant="primary" onClick={handleOpenCreate}>
              {t('admin.categories.createButton')}
            </Button>
          </div>
        ) : (
          <div className="relative">
            {/* Scroll indicator - right side gradient */}
            <div
              className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white dark:from-gray-800 to-transparent pointer-events-none z-10 md:hidden"
              aria-hidden="true"
            />
            <div className="overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600 scrollbar-track-transparent">
              <table className="w-full min-w-[800px]">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700">
                    <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                      ID
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                      {t('admin.categories.englishName')}
                    </th>
                    <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                      {t('admin.categories.frenchName')}
                    </th>
                    <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                      {t('admin.categories.totalIdeas')}
                    </th>
                    <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                      {t('admin.categories.approved')}
                    </th>
                    <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                      {t('admin.categories.pending')}
                    </th>
                    <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                      {t('admin.categories.rejected')}
                    </th>
                    <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                      {t('admin.categories.actions')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {categories.map((category) => (
                    <tr
                      key={category.category_id}
                      className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                    >
                      <td className="py-3 px-4 text-gray-900 dark:text-gray-100">
                        {category.category_id}
                      </td>
                      <td className="py-3 px-4 text-gray-900 dark:text-gray-100">
                        {category.category_name_en}
                      </td>
                      <td className="py-3 px-4 text-gray-900 dark:text-gray-100">
                        {category.category_name_fr}
                      </td>
                      <td className="py-3 px-4 text-center text-gray-700 dark:text-gray-300">
                        {category.total_ideas}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center justify-center px-2 py-1 text-sm font-semibold text-success-700 dark:text-success-300 bg-success-100 dark:bg-success-900/50 rounded-full">
                          {category.approved_ideas}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center justify-center px-2 py-1 text-sm font-semibold text-warning-700 dark:text-warning-300 bg-warning-100 dark:bg-warning-900/50 rounded-full">
                          {category.pending_ideas}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="inline-flex items-center justify-center px-2 py-1 text-sm font-semibold text-error-700 dark:text-error-300 bg-error-100 dark:bg-error-900/50 rounded-full">
                          {category.rejected_ideas}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div
                          className="flex items-center justify-end gap-1"
                          role="group"
                          aria-label={t('admin.categories.actions')}
                        >
                          {/* Edit - Pencil icon */}
                          <button
                            onClick={() => handleOpenEdit(category)}
                            className="p-2 rounded-lg text-gray-500 hover:text-info-600 hover:bg-info-50
                                     dark:text-gray-400 dark:hover:text-info-400 dark:hover:bg-info-900/30
                                     transition-colors focus:outline-none focus:ring-2 focus:ring-info-500"
                            title={t('admin.categories.edit')}
                            aria-label={t('admin.categories.edit')}
                          >
                            <svg
                              className="w-5 h-5"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                              />
                            </svg>
                          </button>

                          {/* Delete - Trash icon */}
                          <button
                            onClick={() => handleOpenDelete(category)}
                            className="p-2 rounded-lg text-gray-500 hover:text-error-600 hover:bg-error-50
                                     dark:text-gray-400 dark:hover:text-error-400 dark:hover:bg-error-900/30
                                     transition-colors focus:outline-none focus:ring-2 focus:ring-error-500"
                            title={t('admin.categories.delete')}
                            aria-label={t('admin.categories.delete')}
                          >
                            <svg
                              className="w-5 h-5"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                              />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog
        open={modalMode === 'create' || modalMode === 'edit'}
        onOpenChange={(open) => !open && resetForm()}
      >
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle className="text-2xl">
              {modalMode === 'create'
                ? t('admin.categories.createNewCategory')
                : t('admin.categories.editCategory')}
            </DialogTitle>
            <DialogDescription>
              {modalMode === 'create'
                ? t('admin.categories.createDescription')
                : t('admin.categories.editDescription')}
            </DialogDescription>
          </DialogHeader>

          {error && (
            <div className="mb-4">
              <Alert variant="error">{error}</Alert>
            </div>
          )}

          <div className="space-y-4">
            <Input
              type="text"
              label={t('admin.categories.englishNameLabel')}
              value={formData.name_en}
              onChange={(e) => setFormData({ ...formData, name_en: e.target.value })}
              placeholder={t('admin.categories.enterEnglishName')}
              disabled={isSubmitting}
              required
            />

            <Input
              type="text"
              label={t('admin.categories.frenchNameLabel')}
              value={formData.name_fr}
              onChange={(e) => setFormData({ ...formData, name_fr: e.target.value })}
              placeholder={t('admin.categories.enterFrenchName')}
              disabled={isSubmitting}
              required
            />

            <Textarea
              label={t('admin.categories.englishDescriptionLabel')}
              value={formData.description_en}
              onChange={(e) => setFormData({ ...formData, description_en: e.target.value })}
              rows={3}
              placeholder={t('admin.categories.optionalEnglishDescription')}
              disabled={isSubmitting}
            />

            <Textarea
              label={t('admin.categories.frenchDescriptionLabel')}
              value={formData.description_fr}
              onChange={(e) => setFormData({ ...formData, description_fr: e.target.value })}
              rows={3}
              placeholder={t('admin.categories.optionalFrenchDescription')}
              disabled={isSubmitting}
            />
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={resetForm} disabled={isSubmitting}>
              {t('admin.categories.cancel')}
            </Button>
            <Button
              variant="primary"
              onClick={modalMode === 'create' ? handleCreate : handleUpdate}
              loading={isSubmitting}
              disabled={isSubmitting}
            >
              {modalMode === 'create' ? t('admin.categories.create') : t('admin.categories.update')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={modalMode === 'delete'} onOpenChange={(open) => !open && resetForm()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-2xl">{t('admin.categories.deleteCategory')}</DialogTitle>
            <DialogDescription>{t('admin.categories.deleteWarning')}</DialogDescription>
          </DialogHeader>

          {error && (
            <div className="mb-4">
              <Alert variant="error">{error}</Alert>
            </div>
          )}

          {selectedCategory && (
            <>
              <p className="text-gray-700 mb-2">{t('admin.categories.deleteConfirmation')}</p>
              <div className="bg-gray-50 p-4 rounded-lg mb-4 border border-gray-200">
                <p className="font-semibold text-gray-900">{getCategoryName(selectedCategory)}</p>
                <p className="text-sm text-gray-600 mt-1">
                  {t('admin.categories.totalIdeasLabel')}: {selectedCategory.total_ideas} (
                  {selectedCategory.approved_ideas} {t('admin.categories.approvedLower')})
                </p>
              </div>

              {selectedCategory.total_ideas > 0 && (
                <div className="mb-4">
                  <Alert variant="warning">{t('admin.categories.cannotDeleteWithIdeas')}</Alert>
                </div>
              )}
            </>
          )}

          <DialogFooter>
            <Button variant="secondary" onClick={resetForm} disabled={isSubmitting}>
              {t('admin.categories.cancel')}
            </Button>
            <Button
              variant="primary"
              onClick={handleDelete}
              loading={isSubmitting}
              disabled={isSubmitting || (selectedCategory?.total_ideas ?? 0) > 0}
              className="bg-error-600 hover:bg-error-700 border-error-600"
            >
              {t('admin.categories.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
