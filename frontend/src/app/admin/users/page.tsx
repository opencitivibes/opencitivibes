'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '@/store/authStore';
import { adminAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { useLocalizedField } from '@/hooks/useLocalizedField';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import {
  UserFilters,
  type UserFilterState,
  emptyFilterState,
  filtersToParams,
} from '@/components/admin/UserFilters';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { UserManagement, UserStatistics } from '@/types';

type ModalMode = 'stats' | 'delete' | null;

// Badge components for reputation display
function TrustBadge({ score }: { score: number }) {
  const { t } = useTranslation();

  if (score >= 70) {
    return (
      <Badge variant="approved" className="text-xs">
        {t('admin.users.badges.trusted')}
      </Badge>
    );
  } else if (score >= 40) {
    return (
      <Badge variant="pending" className="text-xs">
        {t('admin.users.badges.neutral')}
      </Badge>
    );
  } else {
    return (
      <Badge variant="rejected" className="text-xs">
        {t('admin.users.badges.lowTrust')}
      </Badge>
    );
  }
}

function PenaltyBadge({ count, active }: { count: number; active: number }) {
  const { t } = useTranslation();

  if (active > 0) {
    return (
      <Badge variant="rejected" className="text-xs">
        {t('admin.users.badges.penalized', { count: active })}
      </Badge>
    );
  } else if (count > 0) {
    return (
      <Badge variant="pending" className="text-xs">
        {t('admin.users.badges.pastPenalties', { count })}
      </Badge>
    );
  }
  return null;
}

function VoteScoreBadge({ score }: { score: number }) {
  if (score >= 10) {
    return (
      <Badge variant="approved" className="text-xs">
        +{score}
      </Badge>
    );
  } else if (score <= -5) {
    return (
      <Badge variant="rejected" className="text-xs">
        {score}
      </Badge>
    );
  } else if (score !== 0) {
    return (
      <Badge variant="secondary" className="text-xs">
        {score > 0 ? `+${score}` : score}
      </Badge>
    );
  }
  return null;
}

// Pagination component
function Pagination({
  currentPage,
  totalPages,
  onPageChange,
}: {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  const { t } = useTranslation();

  // Generate page numbers to show
  const getPageNumbers = () => {
    const pages: (number | 'ellipsis')[] = [];
    const showPages = 5; // Max pages to show

    if (totalPages <= showPages) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      // Always show first page
      pages.push(1);

      if (currentPage > 3) {
        pages.push('ellipsis');
      }

      // Show pages around current
      const start = Math.max(2, currentPage - 1);
      const end = Math.min(totalPages - 1, currentPage + 1);

      for (let i = start; i <= end; i++) {
        if (!pages.includes(i)) pages.push(i);
      }

      if (currentPage < totalPages - 2) {
        pages.push('ellipsis');
      }

      // Always show last page
      if (!pages.includes(totalPages)) pages.push(totalPages);
    }

    return pages;
  };

  return (
    <div className="flex items-center justify-center gap-2 mt-6">
      <Button
        size="sm"
        variant="secondary"
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
      >
        {t('admin.users.pagination.previous')}
      </Button>

      <div className="flex items-center gap-1">
        {getPageNumbers().map((page, idx) =>
          page === 'ellipsis' ? (
            <span key={`ellipsis-${idx}`} className="px-2 text-gray-500 dark:text-gray-400">
              ...
            </span>
          ) : (
            <button
              key={page}
              onClick={() => onPageChange(page)}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${
                page === currentPage
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {page}
            </button>
          )
        )}
      </div>

      <Button
        size="sm"
        variant="secondary"
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
      >
        {t('admin.users.pagination.next')}
      </Button>
    </div>
  );
}

export default function AdminUsersPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();
  const { formatDate } = useLocalizedField();

  const [users, setUsers] = useState<UserManagement[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [selectedUser, setSelectedUser] = useState<UserManagement | null>(null);
  const [userStats, setUserStats] = useState<UserStatistics | null>(null);
  const [error, setError] = useState<string>('');

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalUsers, setTotalUsers] = useState(0);
  const pageSize = 20;

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchInput, setSearchInput] = useState('');

  // Filter state
  const [filters, setFilters] = useState<UserFilterState>(emptyFilterState);

  const loadUsers = useCallback(
    async (page: number, search?: string, currentFilters?: UserFilterState) => {
      setIsLoading(true);
      try {
        const filterParams = filtersToParams(currentFilters || filters, page, pageSize, search);
        const data = await adminAPI.getAllUsers(filterParams);

        setUsers(data.users);
        setTotalPages(data.total_pages);
        setTotalUsers(data.total);
        setCurrentPage(data.page);
      } catch (err) {
        console.error('Error loading users:', err);
        setError('Failed to load users');
      } finally {
        setIsLoading(false);
      }
    },
    [pageSize, filters]
  );

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
      return;
    }

    loadUsers(1);
  }, [user, router, loadUsers]);

  const handlePageChange = (page: number) => {
    loadUsers(page, searchQuery, filters);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchQuery(searchInput);
    loadUsers(1, searchInput, filters);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setSearchQuery('');
    loadUsers(1, '', filters);
  };

  const handleFilterChange = (newFilters: UserFilterState) => {
    setFilters(newFilters);
    setCurrentPage(1);
    loadUsers(1, searchQuery, newFilters);
  };

  const handleClearFilters = () => {
    setFilters(emptyFilterState);
    setCurrentPage(1);
    loadUsers(1, searchQuery, emptyFilterState);
  };

  const handleOpenStats = async (selectedUser: UserManagement) => {
    setSelectedUser(selectedUser);
    setModalMode('stats');
    setError('');

    try {
      const stats = await adminAPI.getUserStatistics(selectedUser.id);
      setUserStats(stats);
    } catch (err) {
      console.error('Error loading user statistics:', err);
      setError('Failed to load user statistics');
    }
  };

  const handleOpenDelete = (selectedUser: UserManagement) => {
    setSelectedUser(selectedUser);
    setModalMode('delete');
    setError('');
  };

  const handleToggleActive = async (selectedUser: UserManagement) => {
    setIsSubmitting(true);
    setError('');

    try {
      await adminAPI.updateUser(selectedUser.id, {
        is_active: !selectedUser.is_active,
      });
      success('toast.userUpdated');
      await loadUsers(currentPage, searchQuery, filters);
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error toggling user status:', err);
      toastError(axiosError.response?.data?.detail || t('toast.error'), { isRaw: true });
      setError(axiosError.response?.data?.detail || 'Failed to update user');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleAdmin = async (selectedUser: UserManagement) => {
    setIsSubmitting(true);
    setError('');

    try {
      await adminAPI.updateUser(selectedUser.id, {
        is_global_admin: !selectedUser.is_global_admin,
      });
      success('toast.userUpdated');
      await loadUsers(currentPage, searchQuery, filters);
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error toggling admin status:', err);
      toastError(axiosError.response?.data?.detail || t('toast.error'), { isRaw: true });
      setError(axiosError.response?.data?.detail || 'Failed to update user');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!selectedUser) return;

    setIsSubmitting(true);
    setError('');

    try {
      await adminAPI.deleteUser(selectedUser.id);
      success('toast.userDeleted');
      await loadUsers(currentPage, searchQuery, filters);
      closeModal();
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      console.error('Error deleting user:', err);
      toastError(axiosError.response?.data?.detail || t('toast.error'), { isRaw: true });
      setError(
        axiosError.response?.data?.detail || 'Failed to delete user. User may have associated data.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const closeModal = () => {
    setModalMode(null);
    setSelectedUser(null);
    setUserStats(null);
    setError('');
  };

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <PageHeader title={t('admin.users.title')} />

      {/* Global Error */}
      {error && !modalMode && (
        <div className="mb-6">
          <Alert variant="error" dismissible onDismiss={() => setError('')}>
            {error}
          </Alert>
        </div>
      )}

      {/* Filters */}
      <UserFilters filters={filters} onChange={handleFilterChange} onClear={handleClearFilters} />

      {/* Users List */}
      <Card>
        {/* Header with search */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            {t('admin.users.allUsers')} ({totalUsers})
          </h2>

          {/* Search Form */}
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative">
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder={t('admin.users.searchPlaceholder')}
                className="w-64 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              )}
            </div>
            <Button type="submit" variant="secondary" size="sm">
              {t('admin.users.search')}
            </Button>
          </form>
        </div>

        {isLoading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-200 border-t-primary-500"></div>
            <p className="mt-4 text-gray-500">{t('common.loading')}</p>
          </div>
        ) : users.length === 0 ? (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-primary-50 dark:bg-primary-900/30 mb-6">
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
                  d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
              {searchQuery ? t('admin.users.noSearchResults') : t('admin.users.noUsersFound')}
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {searchQuery ? t('admin.users.tryDifferentSearch') : t('admin.users.usersWillAppear')}
            </p>
          </div>
        ) : (
          <>
            <div className="relative">
              {/* Scroll indicator - right side gradient */}
              <div
                className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-white dark:from-gray-800 to-transparent pointer-events-none z-10 md:hidden"
                aria-hidden="true"
              />
              <div className="overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 dark:scrollbar-thumb-gray-600 scrollbar-track-transparent">
                <table className="w-full min-w-[900px]">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                        ID
                      </th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                        {t('admin.users.displayName')}
                      </th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                        {t('admin.users.email')}
                      </th>
                      <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                        {t('admin.users.status')}
                      </th>
                      <th className="text-center py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                        {t('admin.users.reputation')}
                      </th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                        {t('admin.users.created')}
                      </th>
                      <th className="text-right py-3 px-4 font-semibold text-gray-700 dark:text-gray-300">
                        {t('admin.users.actions')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr
                        key={u.id}
                        className="border-b border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                      >
                        <td className="py-3 px-4 text-gray-900 dark:text-gray-100">{u.id}</td>
                        <td className="py-3 px-4">
                          <div className="flex flex-col">
                            <span className="text-gray-900 dark:text-gray-100 font-medium">
                              {u.display_name}
                            </span>
                            <span className="text-gray-500 dark:text-gray-400 text-sm">
                              @{u.username}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-gray-700 dark:text-gray-300">{u.email}</td>
                        <td className="py-3 px-4 text-center">
                          <div className="flex flex-col items-center gap-1">
                            <Badge variant={u.is_active ? 'approved' : 'rejected'}>
                              {u.is_active ? t('admin.users.active') : t('admin.users.inactive')}
                            </Badge>
                            {u.is_global_admin && (
                              <Badge variant="primary">{t('admin.users.admin')}</Badge>
                            )}
                            {u.is_official && (
                              <Badge variant="info">{t('admin.users.official')}</Badge>
                            )}
                            {u.has_category_admin_role && !u.is_global_admin && (
                              <Badge variant="secondary">{t('admin.users.categoryAdmin')}</Badge>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex flex-wrap justify-center gap-1">
                            <TrustBadge score={u.trust_score} />
                            <VoteScoreBadge score={u.vote_score} />
                            <PenaltyBadge count={u.penalty_count} active={u.active_penalty_count} />
                          </div>
                        </td>
                        <td className="py-3 px-4 text-gray-700 dark:text-gray-300 text-sm">
                          {formatDate(u.created_at)}
                        </td>
                        <td className="py-3 px-4">
                          <div
                            className="flex items-center justify-end gap-1"
                            role="group"
                            aria-label={t('admin.users.actions')}
                          >
                            {/* Stats - Chart icon */}
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  onClick={() => handleOpenStats(u)}
                                  className="p-2 rounded-lg text-gray-500 hover:text-info-600 hover:bg-info-50
                                           dark:text-gray-400 dark:hover:text-info-400 dark:hover:bg-info-900/30
                                           transition-colors focus:outline-none focus:ring-2 focus:ring-info-500"
                                  aria-label={t('admin.users.stats')}
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
                                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                                    />
                                  </svg>
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>{t('admin.users.stats')}</p>
                              </TooltipContent>
                            </Tooltip>

                            {/* Toggle Active - Power icon */}
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  onClick={() => handleToggleActive(u)}
                                  disabled={isSubmitting || u.id === user.id}
                                  className={`p-2 rounded-lg transition-colors focus:outline-none focus:ring-2
                                            ${
                                              u.is_active
                                                ? 'text-gray-500 hover:text-warning-600 hover:bg-warning-50 dark:text-gray-400 dark:hover:text-warning-400 dark:hover:bg-warning-900/30 focus:ring-warning-500'
                                                : 'text-gray-500 hover:text-success-600 hover:bg-success-50 dark:text-gray-400 dark:hover:text-success-400 dark:hover:bg-success-900/30 focus:ring-success-500'
                                            }
                                            disabled:opacity-50 disabled:cursor-not-allowed`}
                                  aria-label={
                                    u.is_active
                                      ? t('admin.users.deactivate')
                                      : t('admin.users.activate')
                                  }
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
                                      d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
                                    />
                                  </svg>
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>
                                  {u.is_active
                                    ? t(
                                        'admin.users.deactivateTooltip',
                                        'Prevent user from logging in'
                                      )
                                    : t('admin.users.activateTooltip', 'Allow user to log in')}
                                </p>
                              </TooltipContent>
                            </Tooltip>

                            {/* Toggle Admin - Shield icon */}
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  onClick={() => handleToggleAdmin(u)}
                                  disabled={isSubmitting || u.id === user.id}
                                  className={`p-2 rounded-lg transition-colors focus:outline-none focus:ring-2
                                            ${
                                              u.is_global_admin
                                                ? 'text-primary-500 hover:text-gray-600 hover:bg-gray-100 dark:text-primary-400 dark:hover:text-gray-300 dark:hover:bg-gray-700'
                                                : 'text-gray-500 hover:text-primary-600 hover:bg-primary-50 dark:text-gray-400 dark:hover:text-primary-400 dark:hover:bg-primary-900/30'
                                            }
                                            focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed`}
                                  aria-label={
                                    u.is_global_admin
                                      ? t('admin.users.removeAdmin')
                                      : t('admin.users.makeAdmin')
                                  }
                                >
                                  <svg
                                    className="w-5 h-5"
                                    fill={u.is_global_admin ? 'currentColor' : 'none'}
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                                    />
                                  </svg>
                                </button>
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>
                                  {u.is_global_admin
                                    ? t('admin.users.removeAdminTooltip', 'Remove admin privileges')
                                    : t('admin.users.makeAdminTooltip', 'Grant admin privileges')}
                                </p>
                              </TooltipContent>
                            </Tooltip>

                            {/* Delete - Trash icon */}
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <button
                                  onClick={() => handleOpenDelete(u)}
                                  disabled={u.id === user.id}
                                  className="p-2 rounded-lg text-gray-500 hover:text-error-600 hover:bg-error-50
                                           dark:text-gray-400 dark:hover:text-error-400 dark:hover:bg-error-900/30
                                           transition-colors focus:outline-none focus:ring-2 focus:ring-error-500
                                           disabled:opacity-50 disabled:cursor-not-allowed"
                                  aria-label={t('admin.users.delete')}
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
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>
                                  {t(
                                    'admin.users.deleteTooltip',
                                    'Permanently delete user and all their content'
                                  )}
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={handlePageChange}
              />
            )}
          </>
        )}
      </Card>

      {/* User Statistics Dialog */}
      <Dialog open={modalMode === 'stats'} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl">
              {t('admin.users.userStatisticsTitle')}: {selectedUser?.display_name}
            </DialogTitle>
            <DialogDescription>{t('admin.users.userStatisticsDescription')}</DialogDescription>
          </DialogHeader>

          {error && (
            <div className="mb-4">
              <Alert variant="error">{error}</Alert>
            </div>
          )}

          {!userStats ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-gray-200 border-t-primary-500"></div>
              <p className="mt-4 text-gray-500">{t('admin.users.loadingStatistics')}</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* User Info */}
              <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-2">
                  {t('admin.users.userInformation')}
                </h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.email')}:
                    </span>{' '}
                    <span className="text-gray-900 dark:text-gray-100">{userStats.email}</span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.username')}:
                    </span>{' '}
                    <span className="text-gray-900 dark:text-gray-100">{userStats.username}</span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.status')}:
                    </span>{' '}
                    <span
                      className={
                        userStats.is_active
                          ? 'text-success-600 dark:text-success-400'
                          : 'text-error-600 dark:text-error-400'
                      }
                    >
                      {userStats.is_active ? t('admin.users.active') : t('admin.users.inactive')}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.role')}:
                    </span>{' '}
                    <span className="text-gray-900 dark:text-gray-100">
                      {userStats.is_global_admin
                        ? t('admin.users.globalAdmin')
                        : t('admin.users.user')}
                    </span>
                  </div>
                </div>
              </div>

              {/* Ideas Statistics */}
              <div className="bg-info-50 dark:bg-info-900/30 p-5 rounded-xl border border-info-200 dark:border-info-800">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                  {t('admin.users.ideas')}
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.total')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-gray-900 dark:text-gray-100">
                      {userStats.ideas.total}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.approved')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-success-600 dark:text-success-400">
                      {userStats.ideas.approved}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.pending')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-warning-600 dark:text-warning-400">
                      {userStats.ideas.pending}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.rejected')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-error-600 dark:text-error-400">
                      {userStats.ideas.rejected}
                    </span>
                  </div>
                </div>
              </div>

              {/* Votes Cast */}
              <div className="bg-success-50 dark:bg-success-900/30 p-5 rounded-xl border border-success-200 dark:border-success-800">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                  {t('admin.users.votesCast')}
                </h3>
                <div className="grid grid-cols-3 gap-3 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.total')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-gray-900 dark:text-gray-100">
                      {userStats.votes_cast.total}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.upvotes')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-success-600 dark:text-success-400">
                      {userStats.votes_cast.upvotes}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.downvotes')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-error-600 dark:text-error-400">
                      {userStats.votes_cast.downvotes}
                    </span>
                  </div>
                </div>
              </div>

              {/* Votes Received */}
              <div className="bg-primary-50 dark:bg-primary-900/30 p-5 rounded-xl border border-primary-200 dark:border-primary-800">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                  {t('admin.users.votesReceived')}
                </h3>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.total')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-gray-900 dark:text-gray-100">
                      {userStats.votes_received.total}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.score')}:
                    </span>{' '}
                    <span
                      className={`font-bold text-lg ${
                        userStats.votes_received.score >= 0
                          ? 'text-success-600 dark:text-success-400'
                          : 'text-error-600 dark:text-error-400'
                      }`}
                    >
                      {userStats.votes_received.score}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.upvotes')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-success-600 dark:text-success-400">
                      {userStats.votes_received.upvotes}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.downvotes')}:
                    </span>{' '}
                    <span className="font-bold text-lg text-error-600 dark:text-error-400">
                      {userStats.votes_received.downvotes}
                    </span>
                  </div>
                </div>
              </div>

              {/* Comments */}
              <div className="bg-warning-50 dark:bg-warning-900/30 p-5 rounded-xl border border-warning-200 dark:border-warning-800">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                  {t('admin.users.comments')}
                </h3>
                <div className="text-sm">
                  <span className="text-gray-600 dark:text-gray-400">
                    {t('admin.users.totalCommentsMade')}:
                  </span>{' '}
                  <span className="font-bold text-lg text-gray-900 dark:text-gray-100">
                    {userStats.comments_made}
                  </span>
                </div>
              </div>

              {/* Moderation Stats */}
              <div className="bg-gray-100 dark:bg-gray-800 p-5 rounded-xl border border-gray-300 dark:border-gray-700">
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                  {t('admin.users.moderation')}
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {/* Trust Score */}
                  <div className="col-span-2">
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.trustScore')}:
                    </span>{' '}
                    <span
                      className={`font-bold text-lg ${
                        userStats.moderation.trust_score >= 40
                          ? 'text-success-600 dark:text-success-400'
                          : userStats.moderation.trust_score >= 20
                            ? 'text-warning-600 dark:text-warning-400'
                            : 'text-error-600 dark:text-error-400'
                      }`}
                    >
                      {userStats.moderation.trust_score}/100
                    </span>
                  </div>

                  {/* Flags Received */}
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.flagsReceived')}:
                    </span>{' '}
                    <span
                      className={`font-bold text-lg ${
                        userStats.moderation.flags_received.total > 0
                          ? 'text-error-600 dark:text-error-400'
                          : 'text-gray-900 dark:text-gray-100'
                      }`}
                    >
                      {userStats.moderation.flags_received.total}
                    </span>
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    ({t('admin.users.onIdeas')}: {userStats.moderation.flags_received.on_ideas},{' '}
                    {t('admin.users.onComments')}: {userStats.moderation.flags_received.on_comments}
                    )
                  </div>

                  {/* Penalties */}
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.penaltiesTotal')}:
                    </span>{' '}
                    <span
                      className={`font-bold text-lg ${
                        userStats.moderation.penalties.total > 0
                          ? 'text-error-600 dark:text-error-400'
                          : 'text-gray-900 dark:text-gray-100'
                      }`}
                    >
                      {userStats.moderation.penalties.total}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600 dark:text-gray-400">
                      {t('admin.users.activePenalties')}:
                    </span>{' '}
                    <span
                      className={`font-bold text-lg ${
                        userStats.moderation.penalties.active > 0
                          ? 'text-error-600 dark:text-error-400'
                          : 'text-success-600 dark:text-success-400'
                      }`}
                    >
                      {userStats.moderation.penalties.active}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <DialogFooter>
            <Button variant="secondary" onClick={closeModal}>
              {t('admin.users.close')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete User Confirmation Dialog */}
      <Dialog open={modalMode === 'delete'} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-2xl">{t('admin.users.deleteUser')}</DialogTitle>
            <DialogDescription>{t('admin.users.deleteUserWarning')}</DialogDescription>
          </DialogHeader>

          {error && (
            <div className="mb-4">
              <Alert variant="error">{error}</Alert>
            </div>
          )}

          {selectedUser && (
            <>
              <p className="text-gray-700 mb-2">{t('admin.users.deleteUserConfirmation')}</p>
              <div className="bg-gray-50 p-4 rounded-lg mb-4 border border-gray-200">
                <p className="font-semibold text-gray-900">{selectedUser.display_name}</p>
                <p className="text-sm text-gray-600 mt-1">{selectedUser.email}</p>
              </div>

              <div className="mb-4">
                <Alert variant="warning">{t('admin.users.deleteUserPermanentWarning')}</Alert>
              </div>
            </>
          )}

          <DialogFooter>
            <Button variant="secondary" onClick={closeModal} disabled={isSubmitting}>
              {t('admin.users.cancel')}
            </Button>
            <Button
              variant="primary"
              onClick={handleDelete}
              loading={isSubmitting}
              disabled={isSubmitting}
              className="bg-error-600 hover:bg-error-700 border-error-600"
            >
              {t('admin.users.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
