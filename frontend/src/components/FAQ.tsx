'use client';

import * as React from 'react';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';

interface FAQItem {
  question: string;
  answer: string;
}

interface FAQProps {
  items: FAQItem[];
}

/**
 * FAQ Component using Shadcn Accordion
 *
 * Usage:
 * ```tsx
 * <FAQ items={[
 *   { question: "How do I submit an idea?", answer: "..." },
 *   { question: "What happens after submission?", answer: "..." },
 * ]} />
 * ```
 *
 * TODO: Implement full FAQ page at /faq route
 * TODO: Add FAQ items to i18n translations
 * TODO: Consider backend API for dynamic FAQ management
 */
export function FAQ({ items }: FAQProps) {
  return (
    <Accordion type="single" collapsible className="w-full">
      {items.map((item, index) => (
        <AccordionItem key={index} value={`item-${index}`}>
          <AccordionTrigger className="text-left">{item.question}</AccordionTrigger>
          <AccordionContent>{item.answer}</AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
}
