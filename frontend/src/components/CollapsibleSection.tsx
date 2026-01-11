'use client';

import * as React from 'react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

interface CollapsibleSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  icon?: React.ReactNode;
}

export function CollapsibleSection({
  title,
  children,
  defaultOpen = false,
  icon,
}: CollapsibleSectionProps) {
  return (
    <Accordion type="single" collapsible defaultValue={defaultOpen ? 'item' : ''}>
      <AccordionItem value="item" className="border rounded-lg">
        <AccordionTrigger className="px-4 py-3 hover:no-underline">
          <div className="flex items-center gap-2">
            {icon}
            <span className="font-semibold">{title}</span>
          </div>
        </AccordionTrigger>
        <AccordionContent className="px-4 pb-4">{children}</AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
