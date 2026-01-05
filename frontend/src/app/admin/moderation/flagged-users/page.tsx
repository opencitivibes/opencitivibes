'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { Users, Flag, AlertTriangle, Loader2, RefreshCw, Gavel } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { adminModerationAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { Select } from '@/components/Select';
import { Textarea } from '@/components/Textarea';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { FlaggedUserSummary, PenaltyType } from '@/types/moderation';
import { PENALTY_TYPE_LABELS, getLocalizedLabel } from '@/types/moderation';

export default function FlaggedUsersPage() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();

  const [users, setUsers] = useState<FlaggedUserSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<FlaggedUserSummary | null>(null);
  const [penaltyType, setPenaltyType] = useState<PenaltyType>('warning');
  const [penaltyReason, setPenaltyReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await adminModerationAPI.getFlaggedUsers();
      setUsers(data.users);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to load flagged users:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsLoading(false);
    }
  }, [t, toastError]);

  useEffect(() => {
    if (!user || !user.is_global_admin) {
      router.push('/');
      return;
    }
    loadUsers();
  }, [user, router, loadUsers]);

  const handleIssuePenalty = async () => {
    if (!selectedUser || !penaltyReason.trim()) return;

    setIsSubmitting(true);
    try {
      await adminModerationAPI.issuePenalty(selectedUser.user_id, penaltyType, penaltyReason);
      success(t('adminModeration.penaltyIssued'), { isRaw: true });
      setSelectedUser(null);
      setPenaltyReason('');
      setPenaltyType('warning');
      loadUsers();
    } catch (err) {
      console.error('Failed to issue penalty:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getPenaltyLabel = (penalty: PenaltyType) => {
    return getLocalizedLabel(PENALTY_TYPE_LABELS[penalty], i18n.language);
  };

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <div className="flex justify-between items-center mb-6">
        <PageHeader title={t('adminModeration.flaggedUsers.title')} />
        <div className="flex items-center gap-4">
          <Badge variant="secondary" size="lg">
            {total} {t('adminModeration.flaggedUsers.usersWithFlags')}
          </Badge>
          <Button variant="secondary" onClick={loadUsers} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : users.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="h-12 w-12 mx-auto text-success-500 mb-4" />
            <p className="text-lg font-medium text-gray-900">
              {t('adminModeration.flaggedUsers.empty')}
            </p>
            <p className="text-gray-500">{t('adminModeration.flaggedUsers.emptyDescription')}</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              {t('adminModeration.flaggedUsers.list')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {t('admin.users.username')}
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {t('adminModeration.trustScore')}
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {t('adminModeration.flaggedUsers.totalFlags')}
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {t('adminModeration.flaggedUsers.pendingFlags')}
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {t('admin.users.status')}
                    </th>
                    <th className="text-right py-3 px-4 font-medium text-gray-700">
                      {t('admin.users.actions')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((flaggedUser) => (
                    <tr key={flaggedUser.user_id} className="border-b border-gray-100">
                      <td className="py-3 px-4">
                        <div>
                          <p className="font-medium text-gray-900">@{flaggedUser.username}</p>
                          <p className="text-gray-500">{flaggedUser.display_name}</p>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={
                            flaggedUser.trust_score >= 80
                              ? 'success'
                              : flaggedUser.trust_score >= 50
                                ? 'warning'
                                : 'error'
                          }
                        >
                          {flaggedUser.trust_score}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        <span className="flex items-center gap-1">
                          <Flag className="h-4 w-4 text-gray-400" />
                          {flaggedUser.total_flags_received}
                          <span className="text-gray-400">
                            ({flaggedUser.valid_flags_received} {t('adminModeration.valid')})
                          </span>
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <Badge
                          variant={flaggedUser.pending_flags_count > 0 ? 'error' : 'secondary'}
                        >
                          {flaggedUser.pending_flags_count}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">
                        {flaggedUser.has_active_penalty && flaggedUser.active_penalty_type ? (
                          <Badge variant="error">
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            {getPenaltyLabel(flaggedUser.active_penalty_type)}
                          </Badge>
                        ) : (
                          <Badge variant="success">{t('admin.users.active')}</Badge>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setSelectedUser(flaggedUser)}
                          disabled={flaggedUser.has_active_penalty}
                        >
                          <Gavel className="h-4 w-4 mr-1" />
                          {t('adminModeration.issuePenalty')}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Issue Penalty Dialog */}
      <Dialog open={!!selectedUser} onOpenChange={() => setSelectedUser(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t('adminModeration.dialog.issuePenaltyTitle')}</DialogTitle>
            <DialogDescription>
              {t('adminModeration.dialog.issuePenaltyDescription', {
                username: selectedUser?.username,
              })}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Select
              label={t('adminModeration.dialog.penaltyType')}
              value={penaltyType}
              onChange={(e) => setPenaltyType(e.target.value as PenaltyType)}
            >
              {(Object.keys(PENALTY_TYPE_LABELS) as PenaltyType[]).map((key) => (
                <option key={key} value={key}>
                  {getPenaltyLabel(key)}
                </option>
              ))}
            </Select>

            <Textarea
              label={t('adminModeration.dialog.penaltyReason')}
              value={penaltyReason}
              onChange={(e) => setPenaltyReason(e.target.value)}
              placeholder={t('adminModeration.dialog.penaltyReasonPlaceholder')}
              rows={3}
            />
          </div>

          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => setSelectedUser(null)}
              disabled={isSubmitting}
            >
              {t('common.cancel')}
            </Button>
            <Button
              variant="primary"
              className="bg-error-600 hover:bg-error-700 border-error-600"
              onClick={handleIssuePenalty}
              disabled={isSubmitting || !penaltyReason.trim()}
              loading={isSubmitting}
            >
              {t('adminModeration.dialog.issuePenaltyConfirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
