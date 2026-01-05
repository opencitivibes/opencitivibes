'use client';

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

interface PasswordStrengthIndicatorProps {
  password: string;
}

type StrengthLevel = 'weak' | 'fair' | 'good' | 'strong';

export function PasswordStrengthIndicator({ password }: PasswordStrengthIndicatorProps) {
  const { t } = useTranslation();

  const { strength, score } = useMemo(() => {
    // Backend requires: 12+ chars, uppercase, lowercase, digit, special char
    const hasMinLength = password.length >= 12;
    const hasUppercase = /[A-Z]/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    const hasDigit = /[0-9]/.test(password);
    const hasSpecial = /[^A-Za-z0-9]/.test(password);

    // Count met requirements
    let score = 0;
    if (hasMinLength) score++;
    if (hasUppercase) score++;
    if (hasLowercase) score++;
    if (hasDigit) score++;
    if (hasSpecial) score++;
    if (password.length >= 16) score++; // Bonus for longer passwords

    // Minimum length is mandatory - if not met, always weak
    if (!hasMinLength) {
      return { strength: 'weak' as StrengthLevel, score };
    }

    // All requirements met
    const meetsAllRequirements = hasUppercase && hasLowercase && hasDigit && hasSpecial;

    let strength: StrengthLevel = 'fair'; // At least 12 chars = fair
    if (meetsAllRequirements && score >= 6) strength = 'strong';
    else if (meetsAllRequirements) strength = 'good';

    return { strength, score };
  }, [password]);

  if (!password) return null;

  const colors = {
    weak: 'bg-error-500',
    fair: 'bg-warning-500',
    good: 'bg-info-500',
    strong: 'bg-success-500',
  };

  const widths = {
    weak: 'w-1/4',
    fair: 'w-2/4',
    good: 'w-3/4',
    strong: 'w-full',
  };

  const textColors = {
    weak: 'text-error-600 dark:text-error-400',
    fair: 'text-warning-600 dark:text-warning-400',
    good: 'text-info-600 dark:text-info-400',
    strong: 'text-success-600 dark:text-success-400',
  };

  return (
    <div className="mt-2">
      <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${colors[strength]} ${widths[strength]}`}
          role="progressbar"
          aria-valuenow={score}
          aria-valuemin={0}
          aria-valuemax={6}
          aria-label={t('auth.passwordStrength.label')}
        />
      </div>
      <p className={`text-xs mt-1.5 font-medium ${textColors[strength]}`}>
        {t(`auth.passwordStrength.${strength}`)}
      </p>
    </div>
  );
}
