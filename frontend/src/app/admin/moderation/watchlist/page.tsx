'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslation } from 'react-i18next';
import { Eye, Plus, Trash2, Loader2, RefreshCw, TestTube, Power } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { adminModerationAPI } from '@/lib/api';
import { useToast } from '@/hooks/useToast';
import { Button } from '@/components/Button';
import { Badge } from '@/components/Badge';
import { Input } from '@/components/Input';
import { Select } from '@/components/Select';
import { Textarea } from '@/components/Textarea';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { KeywordEntry, FlagReason } from '@/types/moderation';
import { FLAG_REASON_LABELS, getLocalizedLabel } from '@/types/moderation';

export default function KeywordWatchlistPage() {
  const { t, i18n } = useTranslation();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const { success, error: toastError } = useToast();

  const [keywords, setKeywords] = useState<KeywordEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false);
  const [newKeyword, setNewKeyword] = useState('');
  const [newIsRegex, setNewIsRegex] = useState(false);
  const [newReason, setNewReason] = useState<FlagReason>('spam');
  const [testKeyword, setTestKeyword] = useState('');
  const [testText, setTestText] = useState('');
  const [testResult, setTestResult] = useState<boolean | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadKeywords = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await adminModerationAPI.getWatchlist();
      setKeywords(data);
    } catch (err) {
      console.error('Failed to load watchlist:', err);
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
    loadKeywords();
  }, [user, router, loadKeywords]);

  const handleAddKeyword = async () => {
    if (!newKeyword.trim()) return;

    setIsSubmitting(true);
    try {
      await adminModerationAPI.addKeyword(newKeyword, newIsRegex, newReason);
      success(t('adminModeration.watchlist.keywordAdded'), { isRaw: true });
      setIsAddDialogOpen(false);
      setNewKeyword('');
      setNewIsRegex(false);
      setNewReason('spam');
      loadKeywords();
    } catch (err) {
      console.error('Failed to add keyword:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleActive = async (keyword: KeywordEntry) => {
    try {
      await adminModerationAPI.updateKeyword(keyword.id, { is_active: !keyword.is_active });
      success(
        keyword.is_active
          ? t('adminModeration.watchlist.keywordDisabled')
          : t('adminModeration.watchlist.keywordEnabled'),
        { isRaw: true }
      );
      loadKeywords();
    } catch (err) {
      console.error('Failed to toggle keyword:', err);
      toastError(t('toast.error'), { isRaw: true });
    }
  };

  const handleDeleteKeyword = async (keywordId: number) => {
    if (!confirm(t('adminModeration.watchlist.deleteConfirm'))) return;

    try {
      await adminModerationAPI.deleteKeyword(keywordId);
      success(t('adminModeration.watchlist.keywordDeleted'), { isRaw: true });
      loadKeywords();
    } catch (err) {
      console.error('Failed to delete keyword:', err);
      toastError(t('toast.error'), { isRaw: true });
    }
  };

  const handleTestKeyword = async () => {
    if (!testKeyword.trim() || !testText.trim()) return;

    setIsSubmitting(true);
    try {
      const matches = await adminModerationAPI.testKeyword(testKeyword, testText);
      setTestResult(matches);
    } catch (err) {
      console.error('Failed to test keyword:', err);
      toastError(t('toast.error'), { isRaw: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getReasonLabel = (reason: FlagReason) => {
    return getLocalizedLabel(FLAG_REASON_LABELS[reason], i18n.language);
  };

  if (!user || !user.is_global_admin) {
    return null;
  }

  return (
    <PageContainer maxWidth="7xl" paddingY="normal">
      <div className="flex justify-between items-center mb-6">
        <PageHeader title={t('adminModeration.watchlist.title')} />
        <div className="flex items-center gap-4">
          <Button variant="secondary" onClick={() => setIsTestDialogOpen(true)}>
            <TestTube className="h-4 w-4 mr-2" />
            {t('adminModeration.watchlist.testKeyword')}
          </Button>
          <Button variant="primary" onClick={() => setIsAddDialogOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            {t('adminModeration.watchlist.addKeyword')}
          </Button>
          <Button variant="secondary" onClick={loadKeywords} disabled={isLoading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            {t('common.refresh')}
          </Button>
        </div>
      </div>

      <p className="text-gray-500 mb-6">{t('adminModeration.watchlist.description')}</p>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : keywords.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Eye className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p className="text-lg font-medium text-gray-900">
              {t('adminModeration.watchlist.empty')}
            </p>
            <p className="text-gray-500">{t('adminModeration.watchlist.emptyDescription')}</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              {t('adminModeration.watchlist.keywords')} ({keywords.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {t('adminModeration.watchlist.keyword')}
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {t('adminModeration.watchlist.type')}
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {t('adminModeration.watchlist.autoFlagReason')}
                    </th>
                    <th className="text-left py-3 px-4 font-medium text-gray-700">
                      {t('adminModeration.watchlist.matches')}
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
                  {keywords.map((keyword) => (
                    <tr key={keyword.id} className="border-b border-gray-100">
                      <td className="py-3 px-4">
                        <code className="bg-gray-100 px-2 py-1 rounded text-sm">
                          {keyword.keyword}
                        </code>
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={keyword.is_regex ? 'primary' : 'secondary'}>
                          {keyword.is_regex ? 'Regex' : 'Text'}
                        </Badge>
                      </td>
                      <td className="py-3 px-4">{getReasonLabel(keyword.auto_flag_reason)}</td>
                      <td className="py-3 px-4">{keyword.match_count}</td>
                      <td className="py-3 px-4">
                        <Badge variant={keyword.is_active ? 'success' : 'secondary'}>
                          {keyword.is_active
                            ? t('admin.users.active')
                            : t('adminModeration.watchlist.disabled')}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => handleToggleActive(keyword)}
                          >
                            <Power className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            className="text-error-600 hover:text-error-700"
                            onClick={() => handleDeleteKeyword(keyword.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add Keyword Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t('adminModeration.watchlist.addKeywordTitle')}</DialogTitle>
            <DialogDescription>
              {t('adminModeration.watchlist.addKeywordDescription')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Input
              label={t('adminModeration.watchlist.keyword')}
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              placeholder={t('adminModeration.watchlist.keywordPlaceholder')}
            />

            <div className="flex items-center space-x-2">
              <Checkbox
                id="is-regex"
                checked={newIsRegex}
                onCheckedChange={(checked) => setNewIsRegex(!!checked)}
              />
              <Label htmlFor="is-regex" className="text-sm font-medium cursor-pointer">
                {t('adminModeration.watchlist.isRegex')}
              </Label>
            </div>

            <Select
              label={t('adminModeration.watchlist.autoFlagReason')}
              value={newReason}
              onChange={(e) => setNewReason(e.target.value as FlagReason)}
            >
              {(Object.keys(FLAG_REASON_LABELS) as FlagReason[]).map((key) => (
                <option key={key} value={key}>
                  {getReasonLabel(key)}
                </option>
              ))}
            </Select>
          </div>

          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => setIsAddDialogOpen(false)}
              disabled={isSubmitting}
            >
              {t('common.cancel')}
            </Button>
            <Button
              variant="primary"
              onClick={handleAddKeyword}
              disabled={isSubmitting || !newKeyword.trim()}
              loading={isSubmitting}
            >
              {t('adminModeration.watchlist.add')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Keyword Dialog */}
      <Dialog open={isTestDialogOpen} onOpenChange={setIsTestDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t('adminModeration.watchlist.testKeywordTitle')}</DialogTitle>
            <DialogDescription>
              {t('adminModeration.watchlist.testKeywordDescription')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <Input
              label={t('adminModeration.watchlist.keyword')}
              value={testKeyword}
              onChange={(e) => {
                setTestKeyword(e.target.value);
                setTestResult(null);
              }}
              placeholder={t('adminModeration.watchlist.keywordPlaceholder')}
            />

            <Textarea
              label={t('adminModeration.watchlist.testText')}
              value={testText}
              onChange={(e) => {
                setTestText(e.target.value);
                setTestResult(null);
              }}
              placeholder={t('adminModeration.watchlist.testTextPlaceholder')}
              rows={3}
            />

            {testResult !== null && (
              <div
                className={`p-3 rounded-lg ${testResult ? 'bg-error-50 text-error-700' : 'bg-success-50 text-success-700'}`}
              >
                {testResult
                  ? t('adminModeration.watchlist.matchFound')
                  : t('adminModeration.watchlist.noMatch')}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={() => setIsTestDialogOpen(false)}>
              {t('common.close')}
            </Button>
            <Button
              variant="primary"
              onClick={handleTestKeyword}
              disabled={isSubmitting || !testKeyword.trim() || !testText.trim()}
              loading={isSubmitting}
            >
              <TestTube className="h-4 w-4 mr-2" />
              {t('adminModeration.watchlist.test')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
