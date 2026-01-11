'use client';

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, X } from 'lucide-react';

// Common passwords to block (synced with backend - Finding #10)
const COMMON_PASSWORDS = new Set([
  'password',
  '123456',
  '12345678',
  'qwerty',
  'abc123',
  'monkey',
  '1234567',
  'letmein',
  'trustno1',
  'dragon',
  'baseball',
  'iloveyou',
  'master',
  'sunshine',
  'ashley',
  'bailey',
  'shadow',
  '123123',
  '654321',
  'superman',
  'qazwsx',
  'michael',
  'football',
  'password1',
  'password123',
  'welcome',
  'welcome1',
  'admin',
  'admin123',
  'login',
  'passw0rd',
  'starwars',
  'princess',
  'solo',
  'qwerty123',
  'azerty',
  'aaaaaa',
  '666666',
  '888888',
  '000000',
  '1111111',
]);

// Sequential patterns (synced with backend - Finding #10)
const SEQUENTIAL_NUMBERS = /012|123|234|345|456|567|678|789|890/;
const SEQUENTIAL_LETTERS =
  /abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz/i;
const REPEATED_CHARS = /(.)\1{2,}/;

export interface PasswordValidationResult {
  isValid: boolean;
  errors: string[];
  strength: 'weak' | 'medium' | 'strong';
  score: number; // 0-100
}

/**
 * Validate password strength (synced with backend - Finding #10)
 */
export function validatePassword(password: string): PasswordValidationResult {
  const errors: string[] = [];
  let score = 0;

  // Minimum length (required)
  if (password.length < 8) {
    errors.push('auth.passwordRequirements.minLength');
  } else {
    score += 20;
  }

  // Maximum length (DoS prevention)
  if (password.length > 128) {
    errors.push('auth.passwordRequirements.maxLength');
  }

  // Uppercase (required)
  if (!/[A-Z]/.test(password)) {
    errors.push('auth.passwordRequirements.uppercase');
  } else {
    score += 20;
  }

  // Lowercase (required)
  if (!/[a-z]/.test(password)) {
    errors.push('auth.passwordRequirements.lowercase');
  } else {
    score += 20;
  }

  // Digit (required)
  if (!/\d/.test(password)) {
    errors.push('auth.passwordRequirements.digit');
  } else {
    score += 20;
  }

  // Common password check
  if (COMMON_PASSWORDS.has(password.toLowerCase())) {
    errors.push('auth.passwordRequirements.common');
  } else if (password.length >= 8) {
    score += 10;
  }

  // Sequential patterns
  if (SEQUENTIAL_NUMBERS.test(password)) {
    errors.push('auth.passwordRequirements.sequentialNumbers');
  } else if (password.length >= 8) {
    score += 5;
  }

  if (SEQUENTIAL_LETTERS.test(password)) {
    errors.push('auth.passwordRequirements.sequentialLetters');
  } else if (password.length >= 8) {
    score += 5;
  }

  // Repeated characters
  if (REPEATED_CHARS.test(password)) {
    errors.push('auth.passwordRequirements.repeatedChars');
  }

  // Bonus for length
  if (password.length >= 12) score += 10;
  if (password.length >= 16) score += 10;

  // Bonus for special characters
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score += 10;

  // Cap score at 100
  score = Math.min(100, score);

  // Determine strength
  let strength: 'weak' | 'medium' | 'strong' = 'weak';
  if (score >= 80 && errors.length === 0) {
    strength = 'strong';
  } else if (score >= 60 && errors.length === 0) {
    strength = 'medium';
  }

  return {
    isValid: errors.length === 0,
    errors,
    strength,
    score,
  };
}

interface PasswordStrengthIndicatorProps {
  password: string;
  showRequirements?: boolean;
}

export function PasswordStrengthIndicator({
  password,
  showRequirements = true,
}: PasswordStrengthIndicatorProps) {
  const { t } = useTranslation();

  const validation = useMemo(() => validatePassword(password), [password]);

  const strengthColors = {
    weak: 'bg-red-500',
    medium: 'bg-yellow-500',
    strong: 'bg-green-500',
  };

  const strengthLabels = {
    weak: t('auth.passwordStrength.weak'),
    medium: t('auth.passwordStrength.medium'),
    strong: t('auth.passwordStrength.strong'),
  };

  // Requirements to check
  const requirements = [
    { key: 'auth.passwordRequirements.minLength', met: password.length >= 8 },
    { key: 'auth.passwordRequirements.uppercase', met: /[A-Z]/.test(password) },
    { key: 'auth.passwordRequirements.lowercase', met: /[a-z]/.test(password) },
    { key: 'auth.passwordRequirements.digit', met: /\d/.test(password) },
  ];

  if (!password) {
    return null;
  }

  return (
    <div className="space-y-3">
      {/* Strength Bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs">
          <span className="text-gray-600 dark:text-gray-400">
            {t('auth.passwordStrength.label')}
          </span>
          <span
            className={`font-medium ${
              validation.strength === 'weak'
                ? 'text-red-600 dark:text-red-400'
                : validation.strength === 'medium'
                  ? 'text-yellow-600 dark:text-yellow-400'
                  : 'text-green-600 dark:text-green-400'
            }`}
          >
            {strengthLabels[validation.strength]}
          </span>
        </div>
        <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${strengthColors[validation.strength]}`}
            style={{ width: `${validation.score}%` }}
            role="progressbar"
            aria-valuenow={validation.score}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={t('auth.passwordStrength.label')}
          />
        </div>
      </div>

      {/* Requirements Checklist */}
      {showRequirements && (
        <ul className="space-y-1">
          {requirements.map((req) => (
            <li
              key={req.key}
              className={`flex items-center gap-2 text-xs ${
                req.met ? 'text-green-600 dark:text-green-400' : 'text-gray-500 dark:text-gray-400'
              }`}
            >
              {req.met ? (
                <Check className="w-3 h-3 flex-shrink-0" />
              ) : (
                <X className="w-3 h-3 flex-shrink-0" />
              )}
              <span>{t(req.key)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
