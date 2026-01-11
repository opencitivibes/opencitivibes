'use client';

import * as React from 'react';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { QuestionMarkCircledIcon } from '@radix-ui/react-icons';

interface FormHelpProps {
  content: React.ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
}

export function FormHelp({ content, side = 'right' }: FormHelpProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="inline-flex items-center justify-center w-5 h-5 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
          aria-label="Help"
        >
          <QuestionMarkCircledIcon className="w-4 h-4" />
        </button>
      </PopoverTrigger>
      <PopoverContent side={side} className="max-w-xs text-sm">
        {content}
      </PopoverContent>
    </Popover>
  );
}
