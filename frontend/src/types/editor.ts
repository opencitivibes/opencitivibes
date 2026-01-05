import type { ReactNode } from 'react';

export interface RichTextEditorProps {
  /** Current HTML content */
  value: string;
  /** Called when content changes */
  onChange: (html: string) => void;
  /** Placeholder text (uses translation key if starts with 'editor.') */
  placeholder?: string;
  /** Editor label for accessibility */
  label?: string;
  /** Whether the editor is disabled */
  disabled?: boolean;
  /** Error state */
  error?: boolean;
  /** Success state */
  success?: boolean;
  /** Helper text below editor */
  helperText?: string;
  /** Minimum height in pixels */
  minHeight?: number;
  /** Maximum character count (0 = unlimited) */
  maxLength?: number;
  /** Show character count */
  showCharacterCount?: boolean;
  /** CSS class for container */
  className?: string;
  /** ID for form association */
  id?: string;
}

export interface SimpleRichTextEditorProps extends Omit<RichTextEditorProps, 'minHeight'> {
  /** Number of rows (approximate height) */
  rows?: number;
}

export interface ToolbarButtonProps {
  /** Button icon or text */
  children: ReactNode;
  /** Whether the button is active (format applied) */
  isActive?: boolean;
  /** Click handler */
  onClick: () => void;
  /** Tooltip/title text */
  title: string;
  /** Whether button is disabled */
  disabled?: boolean;
}

export interface RichTextDisplayProps {
  /** HTML content to display */
  content: string;
  /** CSS class for container */
  className?: string;
}

export type EditorMode = 'full' | 'simple';
