'use client';

import * as React from 'react';
import { useTranslation } from 'react-i18next';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { Category } from '@/types';

interface CategorySelectProps {
  categories: Category[];
  value: number | undefined;
  onValueChange: (value: number | undefined) => void;
  placeholder?: string;
  showAllOption?: boolean;
  disabled?: boolean;
  className?: string;
}

export function CategorySelect({
  categories,
  value,
  onValueChange,
  placeholder,
  showAllOption = false,
  disabled = false,
  className,
}: CategorySelectProps) {
  const { t, i18n } = useTranslation();

  const handleValueChange = (val: string) => {
    if (val === 'all' || val === '') {
      onValueChange(undefined);
    } else {
      onValueChange(Number(val));
    }
  };

  return (
    <Select
      value={value?.toString() || (showAllOption ? 'all' : '')}
      onValueChange={handleValueChange}
      disabled={disabled}
    >
      <SelectTrigger className={className}>
        <SelectValue placeholder={placeholder || t('ideas.selectCategory')} />
      </SelectTrigger>
      <SelectContent>
        {showAllOption && <SelectItem value="all">{t('ideas.allCategories')}</SelectItem>}
        {categories.map((category) => (
          <SelectItem key={category.id} value={category.id.toString()}>
            {i18n.language === 'fr' ? category.name_fr : category.name_en}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
