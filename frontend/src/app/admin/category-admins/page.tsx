'use client';

import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { adminAPI, adminRolesAPI, categoryAPI } from '@/lib/api';
import type { AdminRole, Category, UserManagement } from '@/types';
import { UserCog, UserPlus, Trash2, Search, X, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';

export default function CategoryAdminsPage() {
  const { t, i18n, ready } = useTranslation();
  const router = useRouter();
  const { user } = useAuthStore();
  const locale = i18n.language?.substring(0, 2) === 'en' ? 'en' : 'fr';

  // Data state
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [usersMap, setUsersMap] = useState<Map<number, UserManagement>>(new Map());
  const [isLoading, setIsLoading] = useState(true);

  // Modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<UserManagement[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserManagement | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [isAdding, setIsAdding] = useState(false);

  // Check admin access
  useEffect(() => {
    if (user && !user.is_global_admin) {
      router.push('/');
    }
  }, [user, router]);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [rolesRes, categoriesRes] = await Promise.all([
        adminRolesAPI.getAll(),
        categoryAPI.getAll(),
      ]);
      setRoles(rolesRes);
      setCategories(categoriesRes);

      // Fetch user details for roles (if we have roles)
      if (rolesRes.length > 0) {
        const uniqueUserIds = Array.from(new Set(rolesRes.map((r) => r.user_id)));
        const userMap = new Map<number, UserManagement>();

        // Fetch users in batches to avoid N+1 (max page_size is 100)
        const usersResponse = await adminAPI.getAllUsers({ page_size: 100 });
        usersResponse.users.forEach((u) => {
          if (uniqueUserIds.includes(u.id)) {
            userMap.set(u.id, u);
          }
        });
        setUsersMap(userMap);
      }
    } catch {
      toast.error(t('admin.categoryAdmins.loadError'));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Search users for adding
  const handleSearch = async () => {
    if (searchQuery.length < 2) return;
    setIsSearching(true);
    try {
      const response = await adminAPI.getAllUsers({ search: searchQuery, page_size: 10 });
      // Filter out global admins (they already have full access)
      setSearchResults(response.users.filter((u) => !u.is_global_admin));
    } catch {
      toast.error(t('admin.categoryAdmins.searchError'));
    } finally {
      setIsSearching(false);
    }
  };

  const handleAdd = async () => {
    if (!selectedUser || !selectedCategoryId) return;

    // Check if role already exists
    const exists = roles.some(
      (r) => r.user_id === selectedUser.id && r.category_id === selectedCategoryId
    );
    if (exists) {
      toast.error(t('admin.categoryAdmins.alreadyAdmin'));
      return;
    }

    setIsAdding(true);
    try {
      await adminRolesAPI.create({
        user_id: selectedUser.id,
        category_id: selectedCategoryId,
      });
      toast.success(t('admin.categoryAdmins.addSuccess'));
      setShowAddModal(false);
      resetModal();
      fetchData();
    } catch {
      toast.error(t('admin.categoryAdmins.addError'));
    } finally {
      setIsAdding(false);
    }
  };

  const handleDelete = async (roleId: number) => {
    if (!confirm(t('admin.categoryAdmins.removeConfirm'))) return;
    try {
      await adminRolesAPI.delete(roleId);
      toast.success(t('admin.categoryAdmins.removeSuccess'));
      fetchData();
    } catch {
      toast.error(t('admin.categoryAdmins.removeError'));
    }
  };

  const resetModal = () => {
    setSelectedUser(null);
    setSelectedCategoryId(null);
    setSearchQuery('');
    setSearchResults([]);
  };

  const getCategoryName = (categoryId: number): string => {
    const category = categories.find((c) => c.id === categoryId);
    if (!category) return t('admin.categoryAdmins.noCategory');
    return locale === 'en' ? category.name_en : category.name_fr;
  };

  const getUserInfo = (userId: number): { name: string; email: string } => {
    const userInfo = usersMap.get(userId);
    return {
      name: userInfo?.display_name || `User #${userId}`,
      email: userInfo?.email || '',
    };
  };

  // Wait for i18n to be ready and user to be admin
  if (!ready || !user?.is_global_admin) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <UserCog className="w-8 h-8 text-primary-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {t('admin.categoryAdmins.title')}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('admin.categoryAdmins.subtitle')}
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white
            rounded-lg hover:bg-primary-700 transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          {t('admin.categoryAdmins.addButton')}
        </button>
      </div>

      {/* Category Admins List */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('admin.categoryAdmins.currentAdmins')} ({roles.length})
          </h2>
        </div>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
          </div>
        ) : roles.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">{t('admin.categoryAdmins.noAdmins')}</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  {t('admin.categoryAdmins.user')}
                </th>
                <th className="px-6 py-3 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  {t('admin.categoryAdmins.category')}
                </th>
                <th className="px-6 py-3 text-right text-sm font-medium text-gray-600 dark:text-gray-300">
                  {t('admin.categoryAdmins.actions')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {roles.map((role) => {
                const userInfo = getUserInfo(role.user_id);
                return (
                  <tr key={role.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">{userInfo.name}</p>
                        <p className="text-sm text-gray-500">{userInfo.email}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800 dark:bg-primary-900/30 dark:text-primary-300">
                        {getCategoryName(role.category_id)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDelete(role.id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm
                          text-red-600 hover:text-red-700 hover:bg-red-50
                          dark:hover:bg-red-900/20 rounded-lg transition-colors"
                        aria-label={t('admin.categoryAdmins.remove')}
                      >
                        <Trash2 className="w-4 h-4" />
                        {t('admin.categoryAdmins.remove')}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl w-full max-w-md shadow-xl">
            <div className="p-6 border-b border-gray-100 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {t('admin.categoryAdmins.addTitle')}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                {t('admin.categoryAdmins.addDescription')}
              </p>
            </div>

            <div className="p-6 space-y-4">
              {/* Search */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {t('admin.categoryAdmins.searchUser')}
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder={t('admin.categoryAdmins.searchPlaceholder')}
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                      bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  <button
                    onClick={handleSearch}
                    disabled={searchQuery.length < 2 || isSearching}
                    className="px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg
                      hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
                    aria-label={t('admin.categoryAdmins.searchUser')}
                  >
                    <Search className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Search Results */}
              {searchResults.length > 0 && !selectedUser && (
                <ul className="max-h-40 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg divide-y divide-gray-100 dark:divide-gray-700">
                  {searchResults.map((searchUser) => (
                    <li
                      key={searchUser.id}
                      onClick={() => setSelectedUser(searchUser)}
                      className="px-3 py-2 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {searchUser.display_name}
                      </p>
                      <p className="text-xs text-gray-500">{searchUser.email}</p>
                    </li>
                  ))}
                </ul>
              )}

              {/* Selected User */}
              {selectedUser && (
                <div className="p-3 bg-primary-50 dark:bg-primary-900/20 rounded-lg flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">
                      {selectedUser.display_name}
                    </p>
                    <p className="text-sm text-gray-500">{selectedUser.email}</p>
                  </div>
                  <button
                    onClick={() => setSelectedUser(null)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                    aria-label={t('common.cancel')}
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* Category Selector */}
              {selectedUser && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t('admin.categoryAdmins.selectCategory')}
                  </label>
                  <select
                    value={selectedCategoryId ?? ''}
                    onChange={(e) =>
                      setSelectedCategoryId(e.target.value ? Number(e.target.value) : null)
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                      bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    <option value="">{t('admin.categoryAdmins.selectCategory')}</option>
                    {categories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {locale === 'en' ? cat.name_en : cat.name_fr}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-6 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  resetModal();
                }}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800
                  dark:hover:text-gray-200"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleAdd}
                disabled={!selectedUser || !selectedCategoryId || isAdding}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg
                  hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isAdding ? t('common.loading') : t('admin.categoryAdmins.assign')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
