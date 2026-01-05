'use client';

import { useTranslation } from 'react-i18next';
import { Button } from '@/components/Button';
import { Mail, KeyRound } from 'lucide-react';

export type LoginMethod = 'password' | 'email';

interface LoginMethodSelectorProps {
  currentMethod: LoginMethod;
  onMethodChange: (method: LoginMethod) => void;
}

export function LoginMethodSelector({ currentMethod, onMethodChange }: LoginMethodSelectorProps) {
  const { t } = useTranslation();

  return (
    <div className="flex gap-2 p-1 bg-gray-100 dark:bg-gray-800 rounded-lg">
      <Button
        type="button"
        variant={currentMethod === 'password' ? 'primary' : 'ghost'}
        size="sm"
        className="flex-1"
        onClick={() => onMethodChange('password')}
      >
        <KeyRound className="mr-2 h-4 w-4" />
        {t('auth.password')}
      </Button>
      <Button
        type="button"
        variant={currentMethod === 'email' ? 'primary' : 'ghost'}
        size="sm"
        className="flex-1"
        onClick={() => onMethodChange('email')}
      >
        <Mail className="mr-2 h-4 w-4" />
        {t('auth.emailCode')}
      </Button>
    </div>
  );
}
