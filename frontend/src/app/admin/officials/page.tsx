'use client';

import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { adminAPI } from '@/lib/api';
import type { OfficialListItem, PendingOfficialRequest, User } from '@/types';
import {
  Shield,
  UserPlus,
  UserMinus,
  Edit2,
  Search,
  Check,
  X,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuthStore } from '@/store/authStore';
import { useRouter } from 'next/navigation';

export default function AdminOfficialsPage() {
  const { t, ready } = useTranslation();
  const router = useRouter();
  const { user } = useAuthStore();
  const [officials, setOfficials] = useState<OfficialListItem[]>([]);
  const [pendingRequests, setPendingRequests] = useState<PendingOfficialRequest[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Grant modal state
  const [showGrantModal, setShowGrantModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [officialTitle, setOfficialTitle] = useState('');
  const [isGranting, setIsGranting] = useState(false);

  // Edit title state
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState('');

  // Check admin access
  useEffect(() => {
    if (user && !user.is_global_admin) {
      router.push('/');
    }
  }, [user, router]);

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [officialsRes, pendingRes] = await Promise.all([
        adminAPI.officials.getAll(),
        adminAPI.officials.getPendingRequests(),
      ]);
      setOfficials(officialsRes);
      setPendingRequests(pendingRes);
    } catch {
      toast.error(t('admin.officials.loadError'));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Search users for granting
  const handleSearch = async () => {
    if (searchQuery.length < 2) return;
    setIsSearching(true);
    try {
      const response = await adminAPI.getAllUsers({ search: searchQuery, page_size: 10 });
      // Filter out existing officials
      const officialIds = new Set(officials.map((o) => o.id));
      setSearchResults(
        response.users.filter(
          (u) => !officialIds.has(u.id) && !u.is_global_admin
        ) as unknown as User[]
      );
    } catch {
      toast.error(t('admin.officials.searchError'));
    } finally {
      setIsSearching(false);
    }
  };

  const handleGrant = async () => {
    if (!selectedUser) return;
    setIsGranting(true);
    try {
      await adminAPI.officials.grant(selectedUser.id, officialTitle || undefined);
      toast.success(t('admin.officials.grantSuccess'));
      setShowGrantModal(false);
      setSelectedUser(null);
      setOfficialTitle('');
      setSearchQuery('');
      setSearchResults([]);
      fetchData();
    } catch {
      toast.error(t('admin.officials.grantError'));
    } finally {
      setIsGranting(false);
    }
  };

  const handleApproveRequest = async (request: PendingOfficialRequest) => {
    try {
      await adminAPI.officials.grant(request.id, request.official_title_request || undefined);
      toast.success(t('admin.officials.approveSuccess'));
      fetchData();
    } catch {
      toast.error(t('admin.officials.approveError'));
    }
  };

  const handleRejectRequest = async (userId: number) => {
    if (!confirm(t('admin.officials.rejectConfirm'))) return;
    try {
      await adminAPI.officials.rejectRequest(userId);
      toast.success(t('admin.officials.rejectSuccess'));
      fetchData();
    } catch {
      toast.error(t('admin.officials.rejectError'));
    }
  };

  const handleRevoke = async (userId: number) => {
    if (!confirm(t('admin.officials.revokeConfirm'))) return;
    try {
      await adminAPI.officials.revoke(userId);
      toast.success(t('admin.officials.revokeSuccess'));
      fetchData();
    } catch {
      toast.error(t('admin.officials.revokeError'));
    }
  };

  const handleUpdateTitle = async (userId: number) => {
    try {
      await adminAPI.officials.updateTitle(userId, editTitle);
      toast.success(t('admin.officials.titleUpdated'));
      setEditingId(null);
      fetchData();
    } catch {
      toast.error(t('admin.officials.titleError'));
    }
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
          <Shield className="w-8 h-8 text-primary-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {t('admin.officials.title')}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('admin.officials.subtitle')}
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowGrantModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white
            rounded-lg hover:bg-primary-700 transition-colors"
        >
          <UserPlus className="w-4 h-4" />
          {t('admin.officials.addOfficial')}
        </button>
      </div>

      {/* Pending Requests Section */}
      {pendingRequests.length > 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-6 border border-amber-200 dark:border-amber-800">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-amber-600" />
            <h2 className="text-lg font-semibold text-amber-800 dark:text-amber-200">
              {t('admin.officials.pendingRequests')} ({pendingRequests.length})
            </h2>
          </div>
          <div className="space-y-3">
            {pendingRequests.map((request) => (
              <div
                key={request.id}
                className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 rounded-lg shadow-sm"
              >
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {request.display_name}
                  </p>
                  <p className="text-sm text-gray-500">{request.email}</p>
                  {request.official_title_request && (
                    <p className="text-sm text-amber-600 dark:text-amber-400 mt-1">
                      {t('admin.officials.requestedTitle')}: {request.official_title_request}
                    </p>
                  )}
                  <p className="text-xs text-gray-400 mt-1">
                    {t('admin.officials.requestedAt')}:{' '}
                    {new Date(request.official_request_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleApproveRequest(request)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-600 text-white
                      rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Check className="w-4 h-4" />
                    {t('admin.officials.approve')}
                  </button>
                  <button
                    onClick={() => handleRejectRequest(request.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-red-600
                      border border-red-200 dark:border-red-800 rounded-lg
                      hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                  >
                    <X className="w-4 h-4" />
                    {t('admin.officials.reject')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Officials List */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('admin.officials.currentOfficials')} ({officials.length})
          </h2>
        </div>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
          </div>
        ) : officials.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">{t('admin.officials.noOfficials')}</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  {t('admin.officials.user')}
                </th>
                <th className="px-6 py-3 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  {t('admin.officials.officialTitle')}
                </th>
                <th className="px-6 py-3 text-left text-sm font-medium text-gray-600 dark:text-gray-300">
                  {t('admin.officials.verifiedAt')}
                </th>
                <th className="px-6 py-3 text-right text-sm font-medium text-gray-600 dark:text-gray-300">
                  {t('admin.officials.actions')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
              {officials.map((official) => (
                <tr key={official.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                  <td className="px-6 py-4">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">
                        {official.display_name}
                      </p>
                      <p className="text-sm text-gray-500">{official.email}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {editingId === official.id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-gray-600 rounded-lg
                            bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                          placeholder={t('admin.officials.enterTitle')}
                          autoFocus
                        />
                        <button
                          onClick={() => handleUpdateTitle(official.id)}
                          className="p-1.5 text-green-600 hover:text-green-700 hover:bg-green-50 dark:hover:bg-green-900/20 rounded"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditingId(null)}
                          className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span className="text-gray-700 dark:text-gray-300">
                          {official.official_title || (
                            <span className="text-gray-400 italic">
                              {t('admin.officials.noTitle')}
                            </span>
                          )}
                        </span>
                        <button
                          onClick={() => {
                            setEditingId(official.id);
                            setEditTitle(official.official_title || '');
                          }}
                          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                          title={t('admin.officials.editTitle')}
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {official.official_verified_at
                      ? new Date(official.official_verified_at).toLocaleDateString()
                      : '-'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRevoke(official.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm
                        text-red-600 hover:text-red-700 hover:bg-red-50
                        dark:hover:bg-red-900/20 rounded-lg transition-colors"
                    >
                      <UserMinus className="w-4 h-4" />
                      {t('admin.officials.revoke')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Grant Modal */}
      {showGrantModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl w-full max-w-md shadow-xl">
            <div className="p-6 border-b border-gray-100 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {t('admin.officials.grantTitle')}
              </h2>
              <p className="text-sm text-gray-500 mt-1">{t('admin.officials.grantDescription')}</p>
            </div>

            <div className="p-6 space-y-4">
              {/* Search */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {t('admin.officials.searchUser')}
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder={t('admin.officials.searchPlaceholder')}
                    className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                      bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                  <button
                    onClick={handleSearch}
                    disabled={searchQuery.length < 2 || isSearching}
                    className="px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg
                      hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
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
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}

              {/* Title Input */}
              {selectedUser && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    {t('admin.officials.officialTitle')}{' '}
                    <span className="text-gray-400 font-normal">({t('common.optional')})</span>
                  </label>
                  <input
                    type="text"
                    value={officialTitle}
                    onChange={(e) => setOfficialTitle(e.target.value)}
                    placeholder={t('admin.officials.titlePlaceholder')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                      bg-white dark:bg-gray-700 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="p-6 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowGrantModal(false);
                  setSelectedUser(null);
                  setSearchQuery('');
                  setSearchResults([]);
                  setOfficialTitle('');
                }}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800
                  dark:hover:text-gray-200"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleGrant}
                disabled={!selectedUser || isGranting}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg
                  hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isGranting ? t('common.loading') : t('admin.officials.grantStatus')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
