'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { authAPI } from '@/lib/api';
import { getAvatarUrl } from '@/components/Navbar/utils';
import { useToast } from '@/hooks/useToast';
import { Input } from '@/components/Input';
import { Button } from '@/components/Button';
import { Alert } from '@/components/Alert';
import { Card } from '@/components/Card';
import { PageContainer, PageHeader } from '@/components/PageContainer';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { TwoFactorSetup } from '@/components/TwoFactorSetup';
import { TwoFactorDisableDialog } from '@/components/TwoFactorDisableDialog';
import type { UserActivityHistory, TwoFactorStatusResponse } from '@/types';
import IdeaCard from '@/components/IdeaCard';
import { RichTextDisplay } from '@/components/RichTextDisplay';

export default function ProfilePage() {
  const { t } = useTranslation();
  const router = useRouter();
  const { user, fetchUser } = useAuthStore();
  const { success } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [activeTab, setActiveTab] = useState('profile');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Profile form state
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');

  // Password form state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Avatar state
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Activity state
  const [activityData, setActivityData] = useState<UserActivityHistory | null>(null);

  // 2FA state
  const [twoFactorStatus, setTwoFactorStatus] = useState<TwoFactorStatusResponse | null>(null);
  const [twoFactorLoading, setTwoFactorLoading] = useState(false);
  const [showSetupDialog, setShowSetupDialog] = useState(false);
  const [showDisableDialog, setShowDisableDialog] = useState(false);
  const [showRegenerateDialog, setShowRegenerateDialog] = useState(false);
  const [regeneratePassword, setRegeneratePassword] = useState('');
  const [regenerateError, setRegenerateError] = useState('');
  const [newBackupCodes, setNewBackupCodes] = useState<string[] | null>(null);

  useEffect(() => {
    if (!user) {
      router.push('/signin?redirect=/profile');
      return;
    }

    setDisplayName(user.display_name);
    setEmail(user.email);
    if (user.avatar_url) {
      setAvatarPreview(getAvatarUrl(user.avatar_url));
    }

    // Load activity data if on activity tab
    if (activeTab === 'activity') {
      loadActivityData();
    }
  }, [user, router, activeTab]);

  const loadActivityData = async () => {
    try {
      const data = await authAPI.getActivityHistory();
      setActivityData(data);
    } catch (error) {
      console.error('Error loading activity data:', error);
    }
  };

  const load2FAStatus = useCallback(async () => {
    setTwoFactorLoading(true);
    try {
      const status = await authAPI.get2FAStatus();
      setTwoFactorStatus(status);
    } catch (error) {
      console.error('Error loading 2FA status:', error);
    } finally {
      setTwoFactorLoading(false);
    }
  }, []);

  // Load 2FA status when switching to security tab
  useEffect(() => {
    if (activeTab === 'security' && user) {
      load2FAStatus();
    }
  }, [activeTab, user, load2FAStatus]);

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      await authAPI.updateProfile({ display_name: displayName, email });
      await fetchUser();
      success('toast.profileUpdated');
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      setMessage({ type: 'error', text: axiosError.response?.data?.detail || t('common.error') });
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    if (newPassword !== confirmPassword) {
      setMessage({ type: 'error', text: t('profile.passwordMismatch', 'Passwords do not match') });
      setLoading(false);
      return;
    }

    if (newPassword.length < 6) {
      setMessage({
        type: 'error',
        text: t('profile.passwordTooShort', 'Password must be at least 6 characters'),
      });
      setLoading(false);
      return;
    }

    try {
      await authAPI.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      success('toast.passwordChanged');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      setMessage({ type: 'error', text: axiosError.response?.data?.detail || t('common.error') });
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file size (5MB max)
      if (file.size > 5 * 1024 * 1024) {
        setMessage({
          type: 'error',
          text: t('profile.fileTooLarge', 'File size too large. Max 5MB'),
        });
        return;
      }

      // Validate file type
      if (!file.type.startsWith('image/')) {
        setMessage({
          type: 'error',
          text: t('profile.invalidFileType', 'Invalid file type. Only images allowed'),
        });
        return;
      }

      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleAvatarUpload = async () => {
    if (!selectedFile) return;

    setLoading(true);
    setMessage(null);

    try {
      await authAPI.uploadAvatar(selectedFile);
      const updatedUser = await authAPI.getMe();
      await fetchUser();

      // Update avatar preview with the new URL from server
      if (updatedUser.avatar_url) {
        setAvatarPreview(getAvatarUrl(updatedUser.avatar_url));
      }

      success('toast.avatarUploaded');
      setSelectedFile(null);
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      setMessage({ type: 'error', text: axiosError.response?.data?.detail || t('common.error') });
    } finally {
      setLoading(false);
    }
  };

  // 2FA handlers
  const handle2FASetupComplete = () => {
    setShowSetupDialog(false);
    load2FAStatus();
    success('twoFactor.enabledSuccess');
  };

  const handle2FADisableComplete = () => {
    setShowDisableDialog(false);
    load2FAStatus();
    success('twoFactor.disabledSuccess');
  };

  const handleRegenerateBackupCodes = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegenerateError('');
    setTwoFactorLoading(true);

    try {
      const response = await authAPI.regenerateBackupCodes({ password: regeneratePassword });
      setNewBackupCodes(response.backup_codes);
      setRegeneratePassword('');
      load2FAStatus();
      success('twoFactor.backupCodesRegenerated');
    } catch (err) {
      const axiosError = err as import('axios').AxiosError<{ detail: string }>;
      setRegenerateError(axiosError.response?.data?.detail || t('twoFactor.regenerateError'));
    } finally {
      setTwoFactorLoading(false);
    }
  };

  const closeRegenerateDialog = () => {
    setShowRegenerateDialog(false);
    setRegeneratePassword('');
    setRegenerateError('');
    setNewBackupCodes(null);
  };

  if (!user) {
    return null;
  }

  return (
    <PageContainer maxWidth="4xl" paddingY="normal">
      <PageHeader title={t('profile.title', 'My Profile')} />

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-6">
          <TabsTrigger value="profile">{t('profile.profileTab', 'Profile')}</TabsTrigger>
          <TabsTrigger value="security">{t('profile.securityTab', 'Security')}</TabsTrigger>
          <TabsTrigger value="activity">{t('profile.activityTab', 'Activity')}</TabsTrigger>
        </TabsList>

        {/* Error message display - success messages are shown via toast */}
        {message && message.type === 'error' && (
          <div className="mb-6">
            <Alert variant="error" dismissible onDismiss={() => setMessage(null)}>
              {message.text}
            </Alert>
          </div>
        )}

        {/* Profile Tab Content */}
        <TabsContent value="profile" className="space-y-6">
          {/* Avatar Section */}
          <Card>
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              {t('profile.avatar', 'Profile Avatar')}
            </h2>
            <div className="flex items-center space-x-4">
              <div className="flex-shrink-0">
                {avatarPreview ? (
                  <Image
                    src={avatarPreview}
                    alt="Avatar"
                    width={96}
                    height={96}
                    className="h-24 w-24 rounded-full object-cover ring-2 ring-primary-100"
                    unoptimized
                  />
                ) : (
                  <div className="h-24 w-24 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center ring-2 ring-primary-100">
                    <span className="text-3xl text-white font-semibold">
                      {user.display_name?.[0]?.toUpperCase() ?? '?'}
                    </span>
                  </div>
                )}
              </div>
              <div className="flex-1">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  accept="image/*"
                  className="hidden"
                />
                <div className="flex flex-wrap gap-2">
                  <Button variant="secondary" onClick={() => fileInputRef.current?.click()}>
                    {t('profile.chooseFile', 'Choose File')}
                  </Button>
                  {selectedFile && (
                    <Button
                      variant="primary"
                      onClick={handleAvatarUpload}
                      loading={loading}
                      disabled={loading}
                    >
                      {t('profile.uploadAvatar', 'Upload')}
                    </Button>
                  )}
                </div>
                <p className="mt-2 text-sm text-gray-500">
                  {t('profile.avatarHint', 'JPG, PNG, GIF up to 5MB')}
                </p>
              </div>
            </div>
          </Card>

          {/* Profile Information */}
          <Card>
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              {t('profile.information', 'Profile Information')}
            </h2>
            <form onSubmit={handleProfileUpdate} className="space-y-4">
              <Input
                type="text"
                label={t('auth.displayName', 'Display Name')}
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
              />
              <Input
                type="email"
                label={t('auth.email', 'Email')}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <Input
                type="text"
                label={t('auth.username', 'Username')}
                value={user.username}
                disabled
                helperText={t('profile.usernameHint', 'Username cannot be changed')}
              />
              <Button type="submit" variant="primary" loading={loading} disabled={loading}>
                {t('profile.saveChanges', 'Save Changes')}
              </Button>
            </form>
          </Card>
        </TabsContent>

        {/* Security Tab Content */}
        <TabsContent value="security" className="space-y-6">
          {/* Two-Factor Authentication */}
          <Card>
            <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              {t('twoFactor.title', 'Two-Factor Authentication')}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              {t(
                'twoFactor.whatIs2FADescription',
                'Two-factor authentication adds an extra layer of security to your account by requiring a code from your phone in addition to your password.'
              )}
            </p>

            {twoFactorLoading && !twoFactorStatus ? (
              <div className="animate-pulse h-20 bg-gray-200 dark:bg-gray-700 rounded" />
            ) : twoFactorStatus ? (
              <div className="space-y-4">
                {/* Status indicator */}
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('common.status', 'Status')}:
                  </span>
                  {twoFactorStatus.enabled ? (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400">
                      {t('twoFactor.enabled', 'Enabled')}
                    </span>
                  ) : (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
                      {t('twoFactor.disabled', 'Disabled')}
                    </span>
                  )}
                </div>

                {/* Backup codes info (only when enabled) */}
                {twoFactorStatus.enabled &&
                  twoFactorStatus.backup_codes_remaining !== undefined && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">
                          {t('twoFactor.backupCodes', 'Backup Codes')}:
                        </span>
                        <span className="text-sm font-medium">
                          {t('twoFactor.backupCodesRemaining', '{{count}} codes remaining', {
                            count: twoFactorStatus.backup_codes_remaining,
                          })}
                        </span>
                      </div>
                      {twoFactorStatus.backup_codes_remaining <= 2 && (
                        <Alert variant="warning">
                          {t(
                            'twoFactor.lowBackupCodesWarning',
                            'You only have {{count}} backup code(s) left. Consider regenerating new codes.',
                            { count: twoFactorStatus.backup_codes_remaining }
                          )}
                        </Alert>
                      )}
                    </div>
                  )}

                {/* Action buttons */}
                <div className="flex flex-wrap gap-3">
                  {twoFactorStatus.enabled ? (
                    <>
                      <Button variant="secondary" onClick={() => setShowRegenerateDialog(true)}>
                        {t('twoFactor.regenerate', 'Regenerate Backup Codes')}
                      </Button>
                      <Button variant="danger" onClick={() => setShowDisableDialog(true)}>
                        {t('twoFactor.disable', 'Disable 2FA')}
                      </Button>
                    </>
                  ) : (
                    <Button variant="primary" onClick={() => setShowSetupDialog(true)}>
                      {t('twoFactor.enable', 'Enable 2FA')}
                    </Button>
                  )}
                </div>
              </div>
            ) : (
              <Alert variant="error">
                {t('twoFactor.statusError', 'Failed to load 2FA status')}
              </Alert>
            )}
          </Card>

          <Card>
            <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
              {t('profile.changePassword', 'Change Password')}
            </h2>
            <form onSubmit={handlePasswordChange} className="space-y-4">
              <Input
                type="password"
                label={t('profile.currentPassword', 'Current Password')}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
              />
              <Input
                type="password"
                label={t('profile.newPassword', 'New Password')}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                helperText={t('auth.passwordMinLength', 'Minimum 6 characters')}
              />
              <Input
                type="password"
                label={t('profile.confirmPassword', 'Confirm New Password')}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
              <Button type="submit" variant="primary" loading={loading} disabled={loading}>
                {t('profile.changePassword', 'Change Password')}
              </Button>
            </form>
          </Card>

          {/* Data & Privacy Links */}
          <Card>
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              {t('settings.data.title', 'My Data')}
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              {t(
                'settings.data.description',
                'Download a copy of all your personal data in compliance with Law 25.'
              )}
            </p>
            <div className="flex flex-col sm:flex-row gap-3 flex-wrap">
              <Link href="/settings/consent">
                <Button variant="secondary">
                  {t('settings.consent.title', 'Consent Management')}
                </Button>
              </Link>
              <Link href="/settings/data">
                <Button variant="secondary">
                  {t('settings.data.downloadTitle', 'Download My Data')}
                </Button>
              </Link>
              <Link href="/settings/delete-account">
                <Button variant="danger">{t('settings.delete.title', 'Delete My Account')}</Button>
              </Link>
            </div>
          </Card>
        </TabsContent>

        {/* Activity Tab Content */}
        <TabsContent value="activity" className="space-y-6">
          {/* Statistics */}
          {activityData && (
            <>
              <Card>
                <h2 className="text-lg font-medium text-gray-900 mb-6">
                  {t('profile.statistics', 'Your Statistics')}
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="text-center p-5 bg-primary-500/10 dark:bg-primary-500/15 rounded-xl border border-primary-500/30 dark:border-primary-400/30">
                    <div className="text-3xl font-bold text-primary-600 dark:text-primary-400 mb-1">
                      {activityData.ideas_count}
                    </div>
                    <div className="text-sm font-medium text-gray-600 dark:text-gray-300">
                      {t('profile.totalIdeas', 'Total Ideas')}
                    </div>
                  </div>
                  <div className="text-center p-5 bg-success-500/10 dark:bg-success-500/15 rounded-xl border border-success-500/30 dark:border-success-400/30">
                    <div className="text-3xl font-bold text-success-600 dark:text-success-400 mb-1">
                      {activityData.approved_ideas_count}
                    </div>
                    <div className="text-sm font-medium text-gray-600 dark:text-gray-300">
                      {t('profile.approvedIdeas', 'Approved')}
                    </div>
                  </div>
                  <div className="text-center p-5 bg-warning-500/10 dark:bg-warning-500/15 rounded-xl border border-warning-500/30 dark:border-warning-400/30">
                    <div className="text-3xl font-bold text-warning-600 dark:text-warning-400 mb-1">
                      {activityData.pending_ideas_count}
                    </div>
                    <div className="text-sm font-medium text-gray-600 dark:text-gray-300">
                      {t('profile.pendingIdeas', 'Pending')}
                    </div>
                  </div>
                  <div className="text-center p-5 bg-info-500/10 dark:bg-info-500/15 rounded-xl border border-info-500/30 dark:border-info-400/30">
                    <div className="text-3xl font-bold text-info-600 dark:text-info-400 mb-1">
                      {activityData.votes_count}
                    </div>
                    <div className="text-sm font-medium text-gray-600 dark:text-gray-300">
                      {t('profile.votesCast', 'Votes Cast')}
                    </div>
                  </div>
                  <div className="text-center p-5 bg-teal-500/10 dark:bg-teal-500/15 rounded-xl border border-teal-500/30 dark:border-teal-400/30">
                    <div className="text-3xl font-bold text-teal-600 dark:text-teal-400 mb-1">
                      {activityData.comments_count}
                    </div>
                    <div className="text-sm font-medium text-gray-600 dark:text-gray-300">
                      {t('profile.comments', 'Comments')}
                    </div>
                  </div>
                </div>
              </Card>

              {/* Recent Ideas */}
              {activityData.recent_ideas.length > 0 && (
                <Card>
                  <h2 className="text-lg font-medium text-gray-900 mb-4">
                    {t('profile.recentIdeas', 'Recent Ideas')}
                  </h2>
                  <div className="space-y-4">
                    {activityData.recent_ideas.map((idea) => (
                      <IdeaCard key={idea.id} idea={idea} onVoteUpdate={loadActivityData} />
                    ))}
                  </div>
                </Card>
              )}

              {/* Recent Comments */}
              {activityData.recent_comments.length > 0 && (
                <Card>
                  <h2 className="text-lg font-medium text-gray-900 mb-4">
                    {t('profile.recentComments', 'Recent Comments')}
                  </h2>
                  <div className="space-y-3">
                    {activityData.recent_comments.map((comment) => {
                      const isDeleted = comment.is_deleted;
                      const isHidden = comment.is_hidden && !isDeleted;

                      return (
                        <div
                          key={comment.id}
                          className={`border-l-4 pl-4 py-2 rounded-r-lg ${
                            isDeleted
                              ? 'border-error-400 bg-error-50/50'
                              : isHidden
                                ? 'border-warning-400 bg-warning-50/50'
                                : 'border-primary-300 bg-primary-50/50'
                          }`}
                        >
                          {/* Status badges */}
                          {(isDeleted || isHidden) && (
                            <div className="flex items-center gap-2 mb-2">
                              {isDeleted && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-error-100 text-error-800">
                                  {t('profile.commentDeleted', 'Deleted by moderator')}
                                </span>
                              )}
                              {isHidden && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-warning-100 text-warning-800">
                                  {t('profile.commentHidden', 'Hidden (under review)')}
                                </span>
                              )}
                            </div>
                          )}

                          <RichTextDisplay
                            content={comment.content}
                            className={`text-sm ${isDeleted ? 'text-gray-500 line-through' : 'text-gray-700'}`}
                          />

                          {/* Deletion reason */}
                          {isDeleted && comment.deletion_reason && (
                            <div className="mt-2 p-2 bg-error-100/50 rounded text-xs text-error-700">
                              <span className="font-medium">
                                {t('profile.deletionReason', 'Reason')}:
                              </span>{' '}
                              {comment.deletion_reason}
                            </div>
                          )}

                          <div className="flex items-center justify-between mt-1">
                            <p className="text-xs text-gray-500">
                              {new Date(comment.created_at).toLocaleDateString()}
                            </p>
                            <Link
                              href={`/ideas/${comment.idea_id}`}
                              className="text-xs text-primary-600 hover:text-primary-800 hover:underline"
                            >
                              {t('profile.viewIdea', 'View idea')} →
                            </Link>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Card>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>

      {/* 2FA Setup Dialog */}
      <Dialog open={showSetupDialog} onOpenChange={setShowSetupDialog}>
        <DialogContent className="max-w-md">
          <TwoFactorSetup
            onComplete={handle2FASetupComplete}
            onCancel={() => setShowSetupDialog(false)}
          />
        </DialogContent>
      </Dialog>

      {/* 2FA Disable Dialog */}
      <TwoFactorDisableDialog
        open={showDisableDialog}
        onOpenChange={setShowDisableDialog}
        onSuccess={handle2FADisableComplete}
      />

      {/* Regenerate Backup Codes Dialog */}
      <Dialog open={showRegenerateDialog} onOpenChange={closeRegenerateDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t('twoFactor.regenerate', 'Regenerate Backup Codes')}</DialogTitle>
          </DialogHeader>

          {newBackupCodes ? (
            <div className="space-y-4">
              <Alert variant="warning">{t('twoFactor.saveBackupCodes')}</Alert>
              <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 font-mono text-sm grid grid-cols-2 gap-2">
                {newBackupCodes.map((code, index) => (
                  <div key={index} className="text-center">
                    {code}
                  </div>
                ))}
              </div>
              <Button variant="primary" onClick={closeRegenerateDialog} className="w-full">
                {t('twoFactor.setupComplete', 'Done')}
              </Button>
            </div>
          ) : (
            <form onSubmit={handleRegenerateBackupCodes} className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {t(
                  'twoFactor.enterPasswordToRegenerate',
                  'Enter your password to regenerate backup codes:'
                )}
              </p>

              {regenerateError && <Alert variant="error">{regenerateError}</Alert>}

              <Input
                type="password"
                label={t('auth.password', 'Password')}
                value={regeneratePassword}
                onChange={(e) => setRegeneratePassword(e.target.value)}
                required
              />

              <div className="flex gap-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={closeRegenerateDialog}
                  className="flex-1"
                >
                  {t('common.cancel', 'Cancel')}
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  loading={twoFactorLoading}
                  disabled={twoFactorLoading || !regeneratePassword}
                  className="flex-1"
                >
                  {t('twoFactor.regenerate', 'Regenerate')}
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </PageContainer>
  );
}
