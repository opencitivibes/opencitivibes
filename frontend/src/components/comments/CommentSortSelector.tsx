'use client';

import { useTranslation } from 'react-i18next';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

export type CommentSortOrder = 'relevance' | 'newest' | 'oldest' | 'most_liked';

interface CommentSortSelectorProps {
  value: CommentSortOrder;
  onChange: (value: CommentSortOrder) => void;
}

export function CommentSortSelector({ value, onChange }: CommentSortSelectorProps) {
  const { t } = useTranslation();

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">{t('comments.sortBy')}:</span>
      <Select value={value} onValueChange={(v) => onChange(v as CommentSortOrder)}>
        <SelectTrigger className="w-[160px] h-9">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="relevance">{t('comments.sort.relevance')}</SelectItem>
          <SelectItem value="newest">{t('comments.sort.newest')}</SelectItem>
          <SelectItem value="oldest">{t('comments.sort.oldest')}</SelectItem>
          <SelectItem value="most_liked">{t('comments.sort.mostLiked')}</SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
